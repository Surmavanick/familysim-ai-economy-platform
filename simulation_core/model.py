
import mesa
import pandas as pd
import random
import math
from datetime import datetime, timedelta
from agents.base import FamilyMemberAgent
from economy_engine.market import Market
from llm_brain.cognition import ReasoningEngine
from llm_brain.taalas_interface import TaalaLLMInterface, HybridLLMInterface
from events.system import EventsEngine
from world.tbilisi_geography import TBILISI_DISTRICTS
from data.georgia_real_data import GEORGIA_ECONOMIC_INDICATORS
import os
from dotenv import load_dotenv

try:
    from store_engine import shopping_trip as store_engine_shopping_trip
except Exception:
    store_engine_shopping_trip = None

# Load .env so TAALAS_API_KEY is available to every entry point that builds the
# model (simulation_run.py, QUICK_START.py, sim_api.py, dashboard, ...). Without
# this the key stays unset and the model silently drops to heuristic fallback.
load_dotenv()

# Share of a household's budget spendable on a single grocery restock; the rest
# is reserved for other expenses (utilities, events). Drives partial purchase.
_GROCERY_BUDGET_SHARE = 0.6

# Fixed weekly living costs (rent/utilities/transport), deducted on payday so a
# realistic salary does not pile up into an unrealistic surplus. Scales mildly
# with household size (~₾3,200/month for a 4-person family).
_WEEKLY_LIVING_BASE = 400.0
_WEEKLY_LIVING_PER_AGENT = 85.0

# Pantry target (days-of-food per agent) and the fraction below which a household
# goes shopping — checked daily, so they restock when low, not on a fixed weekday.
_PANTRY_TARGET_PER_AGENT = 21
_RESTOCK_AT = 0.4


class Household:
    def __init__(self, household_id, initial_budget, district=None):
        self.id = household_id
        self.budget = initial_budget
        self.inventory = []
        self.events = []
        self.district = district or "Unknown"
        self.retail_history = []
        self.preferred_skus = {}   # category_slug -> barcode (SKU loyalty, persists across trips)

    def log_event(self, msg, time):
        self.events.append(f"[{time}] {msg}")

class FamilySimulation(mesa.Model):
    """Multi-family society simulation kernel with Tbilisi geography and real events."""
    
    def __init__(self, population_config):
        super().__init__()
        self.schedule = mesa.time.RandomActivation(self)
        self.current_time = datetime(2024, 1, 1, 8, 0)
        
        self.market = Market()
        self.reasoning_engine = ReasoningEngine(self)
        
        # ✨ NEW: Use Taalas Cloud API instead of local Ollama
        # Try to use Taalas, fall back to heuristics if not available
        api_key = os.getenv("TAALAS_API_KEY")
        if api_key:
            try:
                self.llm = TaalaLLMInterface(api_key=api_key)
                print("✅ Using Taalas Cloud API (llama3.1-8B)")
            except Exception as e:
                print(f"⚠️ Taalas API failed: {e}")
                print("   Falling back to heuristic reasoning")
                self.llm = HybridLLMInterface()
        else:
            print("⚠️ TAALAS_API_KEY not set. Using hybrid interface (heuristics fallback)")
            self.llm = HybridLLMInterface()
        
        self.events_engine = EventsEngine(self)  # Events system
        
        # ── Macroeconomic parameters (Geostat official 2025–2026) ────────────
        macro = GEORGIA_ECONOMIC_INDICATORS
        self.inflation_rate = macro.get("inflation_rate_annual", 0.02)
        self.gdp_growth = macro.get("gdp_growth_rate", 0.05) / 100  # Geostat 7.5%
        self.unemployment_rate = macro.get("unemployment_rate_national", 0.10)
        self.currency_stability = 0.95
        self.avg_salary_tbilisi = macro.get("average_salary_tbilisi", 2100)
        self.median_household_income = macro.get("median_household_income", 6300)
        self.gdp_per_capita_usd = macro.get("gdp_per_capita_usd", 10296)
        
        self.households = {} # household_id -> Household object
        self.district_distribution = {}  # Track agent distribution across Tbilisi
        self.retail_transactions = []
        
        # Initialize Households and Agents
        for h_data in population_config:
            h_id = h_data['household_id']
            district = h_data.get('district', 'Unknown')
            self.households[h_id] = Household(h_id, h_data['initial_budget'], district)
            # Seed a starting pantry so families don't starve before the first
            # weekly shop. Inventory used to start empty, so hunger spiked for a
            # full week before any restock could happen.
            # Randomised starting pantry (~0.5–3 weeks per member) so households do
            # NOT all deplete and restock in the same weekly wave — a fixed seed made
            # everyone shop in sync, so weekly demand alternated high/low.
            self.households[h_id].inventory = [
                {"id": "seed", "name": "Starter Groceries", "price": 0.0, "category": "Pantry"}
                for _ in range(int(len(h_data['members']) * random.uniform(4, 22)))
            ]

            # Track district distribution
            if district not in self.district_distribution:
                self.district_distribution[district] = 0
            self.district_distribution[district] += 1
            
            for agent_data in h_data['members']:
                agent = FamilyMemberAgent(
                    self.next_id(),
                    self,
                    **agent_data
                )
                agent.household_id = h_id
                self.schedule.add(agent)
            
        print(f"SYSTEM: Society Simulation Initialized with {len(self.households)} households in Tbilisi")
        print(f"SYSTEM: District distribution: {self.district_distribution}")
        llm_status = "✓ Taalas Cloud API" if hasattr(self.llm, 'api_key') else "✓ Fallback (Heuristic)"
        print(f"SYSTEM: LLM Status: {llm_status}")
        print(f"SYSTEM: Events Engine Active")
        print(f"SYSTEM: Macro — GDP Growth: {self.gdp_growth*100:.1f}% | Inflation: {self.inflation_rate*100:.1f}% | Unemployment: {self.unemployment_rate*100:.1f}% | Avg Salary: ₾{self.avg_salary_tbilisi:,.0f}")

    def step(self):
        """Advance simulation."""
        self.schedule.step()
        self.process_household_logic()
        self.events_engine.process_monthly_events()
        self.events_engine.process_random_events()
        
        # Macroeconomics cycle (Every 24 hours)
        if self.current_time.hour == 0:
            self.market.process_macro_cycle()
            # Weekly payday (Sundays). Income lives in the model, not the runner —
            # the old runner-side monthly payday never fired in a 30-day run.
            if self.current_time.weekday() == 6:
                for agent in self.schedule.agents:
                    agent.pay_day()
                # Deduct fixed living costs (rent/utilities/transport) so realistic
                # income does not pile up into an unrealistic surplus.
                for h_id, household in self.households.items():
                    members = sum(1 for a in self.schedule.agents if a.household_id == h_id)
                    living = _WEEKLY_LIVING_BASE + _WEEKLY_LIVING_PER_AGENT * members
                    household.budget = max(0.0, household.budget - living)
            self.log_daily_summary()
            
        self.current_time += timedelta(hours=1)

    def process_household_logic(self):
        hour = self.current_time.hour
        
        for h_id, household in self.households.items():
            h_agents = [a for a in self.schedule.agents if a.household_id == h_id]
            
            # 1. Meals: breakfast & dinner. Two sittings/day keep hunger in a
            # healthy band — a single evening meal (-40) could not outpace the
            # ~39/day hunger growth, so hunger climbed without bound.
            if hour in (8, 19):
                for agent in h_agents:
                    if agent.hunger > 35:
                        if household.inventory:
                            household.inventory.pop()
                            agent.hunger = max(0, agent.hunger - 30)
                        else:
                            agent.stress = min(100, agent.stress + 8)
            
            # 2. Economy Checks
            if hour == 21:
                self.check_household_economy(household, h_agents)

    def get_household_coords(self, household):
        # Every household in a district used to return the SAME single
        # centroid point, so store_engine.select_store's nearby-store search
        # always saw the identical candidate list for an entire district —
        # only the handful of stores closest to that one point could ever be
        # reached, no matter how many households/restocks ran. A deterministic
        # per-household jitter (stable across ticks, keyed by household.id)
        # spreads households realistically across their district's real area,
        # so different households reach different real nearby stores.
        district_meta = TBILISI_DISTRICTS.get(household.district, {})
        base_lat = district_meta.get("lat", 41.7151)
        base_lon = district_meta.get("lon", 44.7945)
        rng = random.Random(f"geo-{household.id}")
        jitter_m = 1800  # ≈ district-scale spread, matches store search radius
        lat_deg = jitter_m / 111_000
        lon_deg = jitter_m / (111_000 * math.cos(math.radians(base_lat)))
        lat = base_lat + (rng.random() - 0.5) * 2 * lat_deg
        lon = base_lon + (rng.random() - 0.5) * 2 * lon_deg
        return lat, lon

    def record_retail_transaction(self, household, shopper, store_name, chain_name, items, total_cost, source):
        category_counts = {}
        total_units = 0
        for item in items:
            qty = item.get("quantity", 1)
            total_units += qty
            category = item.get("category") or item.get("label") or "Other"
            category_counts[category] = category_counts.get(category, 0) + qty
        tx = {
            "timestamp": self.current_time.isoformat(),
            "household_id": household.id,
            "district": household.district,
            "shopper_name": shopper.name,
            "shopper_role": shopper.role,
            "store_name": store_name,
            "chain_name": chain_name,
            "items": items,
            "units": total_units,
            "total_cost": round(total_cost, 2),
            "categories": category_counts,
            "source": source,
        }
        self.retail_transactions.append(tx)
        household.retail_history.append(tx)

    def check_household_economy(self, household, h_agents):
        # Dynamic restock: shop when the pantry runs low (checked daily), not on a
        # fixed weekday — households shouldn't go hungry waiting for Sunday.
        target = len(h_agents) * _PANTRY_TARGET_PER_AGENT
        if len(household.inventory) < target * _RESTOCK_AT:
            self.restock_household(household, h_agents, target - len(household.inventory))

    def restock_household(self, household, agents, qty):
        parents = [a for a in agents if a.role in ["father", "mother"]]
        if not parents or store_engine_shopping_trip is None or qty <= 0:
            return
        shopper = max(parents, key=lambda a: a.personality.get('frugality', 0.5))
        lat, lng = self.get_household_coords(household)
        rng = random.Random(f"{household.id}-{self.current_time.date()}-{shopper.role}")
        trip = store_engine_shopping_trip(lat, lng, household.budget, shopper.role,
                                          rng=rng, preferred_skus=household.preferred_skus)
        items = (trip["basket"]["items"] if trip else []) or []
        if not trip or not items:
            return

        # Option A: realistic per-line quantities to meet the household's need.
        base, rem = divmod(qty, len(items))
        for idx, it in enumerate(items):
            it["quantity"] = base + (1 if idx < rem else 0)
        items = [it for it in items if it["quantity"] > 0]

        # Partial purchase: reserve part of the budget for non-grocery expenses,
        # then buy frugally — cheapest staples first, as many units as fit. A
        # short household buys less and leans cheap instead of overspending or
        # writing a junk fallback transaction.
        affordable = household.budget * _GROCERY_BUDGET_SHARE
        cost = round(sum(it["price"] * it["quantity"] for it in items), 2)
        if cost > affordable:
            items.sort(key=lambda it: it["price"])
            kept, spent = [], 0.0
            for it in items:
                max_q = int((affordable - spent) // it["price"])
                if max_q <= 0:
                    continue
                it["quantity"] = min(it["quantity"], max_q)
                spent += it["price"] * it["quantity"]
                kept.append(it)
            items, cost = kept, round(spent, 2)

        if not items or cost <= 0:
            for a in agents:
                a.stress = min(100, a.stress + 5)   # genuinely cannot afford groceries
            return

        household.budget -= cost
        expanded = []
        for it in items:
            expanded.extend([it] * it["quantity"])
        household.inventory.extend(expanded)
        self.record_retail_transaction(
            household=household,
            shopper=shopper,
            store_name=trip["store"]["name"],
            chain_name=trip["store"]["chain"],
            items=items,
            total_cost=cost,
            source="store_engine",
        )
        if random.random() < 0.05:
            print(f"[ECON] H{household.id} ({shopper.name}) restocked at {trip['store']['name']} — ₾{cost:.2f}, budget ₾{household.budget:.2f}")

    def log_daily_summary(self):
        avg_budget = sum([h.budget for h in self.households.values()]) / len(self.households)
        avg_stress = sum([a.stress for a in self.schedule.agents]) / len(self.schedule.agents)
        avg_health = sum([a.health for a in self.schedule.agents]) / len(self.schedule.agents)
        employed = sum([1 for a in self.schedule.agents if getattr(a, 'employed', True)])
        print(f"[DAY {self.current_time.date()}] Pop: {len(self.schedule.agents)} | Employed: {employed}/{len(self.schedule.agents)} | "
              f"Avg Budget: ₾{avg_budget:.2f} | Avg Stress: {avg_stress:.1f} | Avg Health: {avg_health:.1f} | "
              f"Macro: GDP+{self.gdp_growth*100:.1f}% Inf+{self.inflation_rate*100:.1f}%")
