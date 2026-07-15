import mesa
import random


class FamilyMemberAgent(mesa.Agent):
    """Advanced agent with complex needs, planning, memory, and LLM-powered reasoning."""
    
    def __init__(self, unique_id, model, name, age, role, personality, district=None):
        super().__init__(unique_id, model)
        self.name = name
        self.age = age
        self.role = role
        self.personality = personality # frugality, status_drive, patience, impulsivity
        self.household_id = None
        self.district = district or "Unknown"  # Tbilisi district
        
        # Extended Needs Hierarchy
        self.hunger = 20.0
        self.comfort = 80.0
        self.fun = 50.0
        self.health = 100.0
        self.stress = 10.0
        
        # Irrationality and Habits
        self.impulsivity = personality.get('impulsivity', random.random())
        self.habits = [] # Frequent product IDs
        self.mood = "neutral"
        
        # Memory and Cognition
        self.memory_events = []
        self.product_preferences = {} # product_id -> preference_score 
        self.store_loyalty = {} # store_name -> score
        self.relationships = {} # {name: {"affinity": float, "trust": float}}
        self.accrued_salary = 0.0
        
        # LLM reasoning cache
        self.last_reasoning = None
        self.reasoning_cooldown = 0

    def step(self):
        self.update_needs()
        self.calculate_stress()
        self.reconcile_social_dynamics()
        self.apply_irrationality()
        
        # Rare LLM reasoning - only a few times per month to limit API cost.
        # Trigger for genuinely stressed OR cash-strapped agents (stress saturates
        # around ~73, so the old stress>75 gate almost never fired).
        if self.model.current_time.hour == 21 and self.reasoning_cooldown <= 0:
            household = self.model.households[self.household_id]
            if (self.stress > 70 or household.budget < 400) and random.random() < 0.2:
                context = self.model.reasoning_engine.evaluate_thinking_need(self)
                if context:
                    # Build a real prompt and call the LLM correctly. Previously a
                    # context dict was passed where max_tokens was expected, which
                    # raised inside think() and silently dropped to the heuristic.
                    prompt = (
                        f"You are {self.name}, a {self.role} in a Tbilisi family. "
                        f"Stress {self.stress:.0f}/100, household budget ₾{household.budget:.0f}, "
                        f"pantry {len(household.inventory)} items. "
                        f"In under 10 words, what is your next move to cope?"
                    )
                    try:
                        self.last_reasoning = self.model.llm.think(prompt, max_tokens=30)
                    except Exception as exc:
                        self.last_reasoning = f"Heuristic fallback: preserve cash and reduce stress ({exc.__class__.__name__})"
                    self.model.reasoning_engine.process_decision(self, context)
                    self.reasoning_cooldown = random.randint(5, 15)  # Cooldown 5-15 days
        
        if self.reasoning_cooldown > 0:
            self.reasoning_cooldown -= (1/24)  # Decrement per hour
                
        self.execute_routine()
        
    def update_needs(self):
        # All needs are bounded to [0, 100]. Previously they accumulated without
        # limit: hunger ran to ~280, fun and health went deeply negative.
        self.hunger = min(100, self.hunger + 1.5)
        self.fun = max(0, self.fun - 0.3)
        self.comfort = max(0, self.comfort - 0.2)
        if self.hunger >= 90:
            self.health = max(0, self.health - 0.5)    # starving damages health
        elif self.hunger < 40:
            self.health = min(100, self.health + 0.2)  # well-fed slowly recovers
        if self.fun < 10: self.stress += 1.0

    def apply_irrationality(self):
        """Impulsive behavior based on stress and personality."""
        if self.stress > 70 and self.impulsivity > 0.6:
            if random.random() < 0.05:
                self.perform_impulsive_purchase()

    def perform_impulsive_purchase(self):
        # Buy something fun even if expensive
        store = random.choice(self.model.market.stores)
        product = store.get_random_by_category("Pantry")
        if product:
            household = self.model.households[self.household_id]
            if household.budget >= product['price']:
                household.budget -= product['price']
                household.inventory.append(product)
                store.record_sale(product['id'])
                self.stress = max(0, self.stress - 20)
                self.fun = min(100, self.fun + 25)
                print(f"[IMPULSE] {self.name} ({household.district}) spent ₾{product['price']:.2f} on {product['name']} due to stress.")

    def calculate_stress(self):
        household = self.model.households[self.household_id]
        finance_stress = (3000 - household.budget) / 100 if household.budget < 500 else 0
        hunger_stress = self.hunger / 10 if self.hunger > 50 else 0
        health_stress = (100 - self.health) / 5
        self.stress = min(100, max(0, finance_stress + hunger_stress + health_stress))

    def plan_purchase(self, product_name):
        household = self.model.households[self.household_id]
        cheapest_option = self.model.market.get_cheapest_store_for_product(product_name)
        if not cheapest_option: return None
        store, product = cheapest_option
        if household.budget < product['price']: return None
        return store, product

    def reconcile_social_dynamics(self):
        # Stress propagation from household members
        h_agents = [a for a in self.model.schedule.agents if a.household_id == self.household_id]
        avg_h_stress = sum([a.stress for a in h_agents]) / len(h_agents)
        if avg_h_stress > 40: self.stress += 0.2

    def add_memory(self, event_msg):
        self.memory_events.append({"time": str(self.model.current_time), "event": event_msg})
        if len(self.memory_events) > 20: self.memory_events.pop(0)

    def execute_routine(self):
        hour = self.model.current_time.hour
        if hour >= 23 or hour <= 6: self.sleep()
        elif 9 <= hour <= 17: self.work_or_school()
        elif 18 <= hour <= 19: self.socialize()
        elif 20 <= hour <= 21: self.socialize_with_neighbors()
            
    def sleep(self):
        self.health = min(100, self.health + 1.0)
        self.comfort = min(100, self.comfort + 1.0)
        self.hunger = min(100, self.hunger + 0.4)

    def work_or_school(self):
        # ₾10/work-hour × 9 work-hours/day × 7 ≈ ₾630/week gross → ~₾504 net after
        # 20% tax ≈ ₾2,180/month per working adult (≈ Tbilisi avg salary), paid weekly.
        if self.role != "child": self.accrued_salary += 10.0
        else: self.fun = max(0, self.fun - 0.3)

    def socialize(self):
        self.fun = min(100, self.fun + 3.0)  # leisure / family time restores fun
        h_agents = [a for a in self.model.schedule.agents if a.household_id == self.household_id and a != self]
        if not h_agents: return
        target = random.choice(h_agents)
        rel = self.relationships.get(target.name, {"affinity": 50, "trust": 50})
        if self.stress > 60:
            rel["affinity"] -= 2
            if random.random() < 0.05:
                print(f"[SOCIAL] Conflict in H{self.household_id} ({self.district}): {self.name} is stressed.")
        else:
            rel["affinity"] += 0.5
        self.relationships[target.name] = rel

    def socialize_with_neighbors(self):
        """Interact with agents from other households. Spread trends/loyalty."""
        self.fun = min(100, self.fun + 2.0)  # socialising with neighbours is fun
        others = [a for a in self.model.schedule.agents if a.household_id != self.household_id]
        if not others: return
        neighbor = random.choice(others)
        
        # Trend propagation: If neighbor is loyal to a store, you might get curious
        neighbor_loyalty = neighbor.store_loyalty
        for store_name, score in neighbor_loyalty.items():
            if score > 70:
                current_score = self.store_loyalty.get(store_name, 0)
                self.store_loyalty[store_name] = min(100, current_score + 5)
                if random.random() < 0.01:
                    print(f"[TREND] {self.name} heard good things about {store_name} from {neighbor.name}.")

    def pay_day(self):
        tax = self.accrued_salary * 0.2
        net = self.accrued_salary - tax
        self.model.households[self.household_id].budget += net
        self.accrued_salary = 0
        if random.random() < 0.1:
            print(f"[INCOME] {self.name} received salary ₾{net:.2f} (after 20% tax)")

class FatherAgent(FamilyMemberAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = "father"

class MotherAgent(FamilyMemberAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = "mother"

class ChildAgent(FamilyMemberAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = "child"

class GrandparentAgent(FamilyMemberAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = "grandparent"
