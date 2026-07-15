#!/usr/bin/env python3
"""
FamilySim Simulation API — port 3001
Stateful: tracks sim_time, accrued salary, household budgets across steps.
Agents are passed in on each /step call; positions owned by the JS frontend.

GET  /api/state  → {sim_time, step_count, status}
POST /api/step   → body: {agents:[{id,role,district,household_id,stress,budget,age,name,_hunger,_fun,_health},...]}
                ← {agents:[{id,stress,budget,activity,_hunger,_fun,_health},...], events:[...], sim_time, step_count}
"""
import json, random, sys, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

# Optional store engine — silently falls back if DB or stores.json missing
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from store_engine import shopping_trip as _shopping_trip
    _USE_STORE_ENGINE = True
except Exception as _se_err:
    _USE_STORE_ENGINE = False
    print(f"[SIM API] store_engine unavailable ({_se_err}), using random baskets", flush=True)

# ─── Simulation state (module-level, persistent across requests) ─────────────
_sim_time  = datetime.now().replace(minute=0, second=0, microsecond=0)
_step      = 0
_accrued   = {}      # agent_id  -> float  (salary not yet paid out)
_hh_budget = {}      # household_id -> float
_hh_seen   = set()   # households initialised from incoming agent data
_month_done = set()  # year-month keys already processed for monthly events

ACTIVITIES = {
    "father":      ["Work", "Home", "Shopping", "Socializing"],
    "mother":      ["Home", "Shopping", "Work", "Errands"],
    "child":       ["School", "Home", "Play", "Studying"],
    "grandparent": ["Home", "Market", "Socializing", "Rest"],
}
BUDGET_SHARE = {"father": 1.0, "mother": 0.60, "grandparent": 0.28, "child": 0.0}

GEO_EVENTS = [
    {"name": "New Year Bonus",       "type": "income",  "amount": 300, "months": [1],       "prob": 0.70},
    {"name": "Easter Expenses",      "type": "expense", "amount": 150, "months": [4],       "prob": 0.90},
    {"name": "School Year Expenses", "type": "expense", "amount": 200, "months": [9],       "prob": 0.90},
    {"name": "Winter Heating Bills", "type": "expense", "amount": 120, "months": [11,12,1,2],"prob": 0.80},
    {"name": "Summer Tourism Bonus", "type": "income",  "amount": 250, "months": [7, 8],    "prob": 0.30},
]


def _imp(agent_id: str) -> float:
    """Deterministic impulsivity 0.20–0.78 per agent, stable across steps."""
    try:
        n = int(agent_id.split("-")[-1])
    except (ValueError, IndexError):
        n = abs(hash(agent_id)) % 1000
    return 0.20 + (n % 58) / 100.0


def step_simulation(agents_in: list) -> dict:
    global _sim_time, _step

    _step     += 1
    _sim_time += timedelta(hours=1)
    hour       = _sim_time.hour
    day        = _sim_time.day
    month      = _sim_time.month
    weekday    = _sim_time.weekday()   # 0=Mon … 6=Sun
    month_key  = f"{_sim_time.year}-{month}"

    events_out = []

    # ── Initialise household budgets from first-seen father ──────────────────
    for a in agents_in:
        hh = a.get("household_id", "")
        if not hh:
            continue
        if hh not in _hh_seen and a.get("role") == "father":
            _hh_budget[hh] = float(a.get("budget", 1000))
            _hh_seen.add(hh)
        if hh not in _hh_budget:
            _hh_budget[hh] = float(a.get("budget", 1000))

    # ── Monthly geo-economic events (once per month, day=1 hour=0) ───────────
    if day == 1 and hour == 0 and month_key not in _month_done:
        _month_done.add(month_key)
        for ev in GEO_EVENTS:
            if month in ev["months"] and random.random() < ev["prob"]:
                for hh in _hh_budget:
                    if ev["type"] == "income":
                        _hh_budget[hh] = min(_hh_budget[hh] + ev["amount"], 25000)
                    else:
                        _hh_budget[hh] = max(0.0, _hh_budget[hh] - ev["amount"])
                events_out.append({
                    "label":     ev["name"],
                    "icon":      "+" if ev["type"] == "income" else "-",
                    "tone":      "good" if ev["type"] == "income" else "warn",
                    "agentName": "All households",
                    "district":  "City-wide",
                    "agentId":   None,
                })

    # ── Precompute household-average stress for social propagation ───────────
    hh_stress_list: dict = {}
    for a in agents_in:
        hh = a.get("household_id", "")
        if hh not in hh_stress_list:
            hh_stress_list[hh] = []
        hh_stress_list[hh].append(float(a.get("stress", 30)))

    is_sunday_morning = (weekday == 6 and hour == 10)

    # ── Per-agent simulation step ────────────────────────────────────────────
    agents_out = []
    for a in agents_in:
        aid      = a.get("id", "")
        role     = a.get("role", "father")
        district = a.get("district", "Unknown")
        hh       = a.get("household_id", "")
        name     = a.get("name", "Agent")
        stress   = float(a.get("stress", 30))
        age      = int(a.get("age", 30))
        imp      = _imp(aid)
        lat          = float(a.get("lat", 41.720))
        lng          = float(a.get("lng", 44.780))
        store_lat_out = None
        store_lng_out = None

        # Internal per-agent state (passed back to us from previous response)
        hunger = float(a.get("_hunger", 25.0)) + 1.5
        fun    = float(a.get("_fun",    50.0)) - 0.5
        health = float(a.get("_health", 90.0))

        if hunger > 80:
            health -= 0.5
        if fun < 10:
            stress += 1.0

        # ── Time-of-day routine ──────────────────────────────────────────────
        if hour >= 23 or hour <= 6:
            activity = "Sleep"
            health   = min(100.0, health + 1.0)
            hunger  += 0.4

        elif 7 <= hour <= 8:
            if role in ("father", "mother"):
                activity = "Commuting"        # morning commute to work
            elif role == "child":
                fun     -= 0.5
                activity = "School"
            else:
                activity = "Home"

        elif 9 <= hour <= 17:
            if is_sunday_morning and role in ("mother", "father"):
                hh_b = _hh_budget.get(hh, 0.0)
                store_lat_out = store_lng_out = None
                if hh_b >= 5.0:
                    if _USE_STORE_ENGINE:
                        try:
                            rng_se = random.Random(hash(aid + str(day) + str(month)))
                            trip   = _shopping_trip(lat, lng, hh_b, role, rng=rng_se)
                        except Exception:
                            trip = None
                    else:
                        trip = None
                    if trip:
                        spend          = trip["cost"]
                        store_lat_out  = trip["store"]["lat"]
                        store_lng_out  = trip["store"]["lng"]
                        ev_label       = trip["event_label"]
                    else:
                        spend    = round(random.uniform(20, 80), 2)
                        ev_label = f"Grocery shopping ₾{spend:.0f}"
                    if _hh_budget.get(hh, 0.0) >= spend:
                        _hh_budget[hh] -= spend
                        hunger = max(0.0, hunger - 20.0)
                        activity = "Shopping"
                        events_out.append({
                            "label":     ev_label,
                            "icon":      "🛒",
                            "tone":      "mute",
                            "agentName": name,
                            "district":  district,
                            "agentId":   aid,
                            "store_lat": store_lat_out,
                            "store_lng": store_lng_out,
                        })
                    else:
                        activity = "Home"
                else:
                    activity = "Home"
            elif role == "child":
                fun     -= 1.0
                activity = "School"
            else:
                _accrued[aid] = _accrued.get(aid, 0.0) + 10.0   # ₾10/work-hour
                activity = "Work"

        elif 18 <= hour <= 19:
            if role in ("father", "mother"):
                activity = "Commuting"        # evening commute home
            else:
                activity = "Home"

        else:
            opts     = ACTIVITIES.get(role, ["Home"])
            activity = opts[_step % len(opts)]

        # ── Evening meal (19:00) ─────────────────────────────────────────────
        if hour == 19 and hunger > 50:
            meal = 8.0
            if _hh_budget.get(hh, 0.0) >= meal:
                _hh_budget[hh] -= meal
                hunger = max(0.0, hunger - 40.0)
            else:
                stress += 8.0
                if random.random() < 0.15:
                    events_out.append({
                        "label":     "Household cannot afford meals",
                        "icon":      "▲",
                        "tone":      "alert",
                        "agentName": name,
                        "district":  district,
                        "agentId":   aid,
                    })

        # ── Monthly payday (1st of month 09:00) ──────────────────────────────
        if day == 1 and hour == 9 and role != "child":
            sal = _accrued.get(aid, 0.0)
            if sal > 0.0:
                net = sal * 0.80   # 20 % income tax
                _hh_budget[hh] = _hh_budget.get(hh, 0.0) + net
                _accrued[aid]  = 0.0
                if random.random() < 0.12:
                    events_out.append({
                        "label":     f"Salary received ₾{net:.0f}",
                        "icon":      "₾",
                        "tone":      "good",
                        "agentName": name,
                        "district":  district,
                        "agentId":   aid,
                    })

        # ── Household stress propagation ──────────────────────────────────────
        hh_members_stress = hh_stress_list.get(hh, [stress])
        avg_hh_stress = sum(hh_members_stress) / len(hh_members_stress)
        if avg_hh_stress > 40:
            stress += 0.2

        # ── Finance-driven stress ─────────────────────────────────────────────
        hh_b         = _hh_budget.get(hh, 500.0)
        fin_stress   = max(0.0, (500.0 - hh_b) / 50.0) if hh_b < 500.0 else 0.0
        hun_stress   = hunger / 10.0 if hunger > 50.0 else 0.0
        hlth_stress  = (100.0 - health) / 5.0
        target_st    = fin_stress + hun_stress + hlth_stress
        stress       = min(100.0, max(0.0, stress * 0.95 + target_st * 0.05))

        # ── Impulsive purchase ────────────────────────────────────────────────
        if stress > 70 and imp > 0.55 and random.random() < 0.015:
            cost = round(random.uniform(12, 55), 2)
            if _hh_budget.get(hh, 0.0) >= cost:
                _hh_budget[hh] -= cost
                stress = max(0.0, stress - 20.0)
                fun    = min(100.0, fun + 25.0)
                events_out.append({
                    "label":     f"Impulsive buy ₾{cost:.0f}",
                    "icon":      "!",
                    "tone":      "warn",
                    "agentName": name,
                    "district":  district,
                    "agentId":   aid,
                })

        # ── Family tension (evening, high stress) ─────────────────────────────
        if 18 <= hour <= 22 and stress > 65 and random.random() < 0.008:
            events_out.append({
                "label":     "Household tension",
                "icon":      "⚡",
                "tone":      "alert",
                "agentName": name,
                "district":  district,
                "agentId":   aid,
            })

        # ── Healthcare emergency (rare) ───────────────────────────────────────
        if random.random() < 0.0003:
            cost = round(random.uniform(200, 800))
            _hh_budget[hh] = max(0.0, _hh_budget.get(hh, 0.0) - cost)
            stress += 15.0
            health = max(0.0, health - 15.0)
            events_out.append({
                "label":     f"Healthcare emergency ₾{cost}",
                "icon":      "🏥",
                "tone":      "alert",
                "agentName": name,
                "district":  district,
                "agentId":   aid,
            })

        # ── Pharmacy visit when health low (evenings) ────────────────────────
        if 18 <= hour <= 21 and health < 60 and random.random() < 0.08:
            if _USE_STORE_ENGINE:
                try:
                    from store_engine import pharmacy_trip as _pharmacy_trip
                    rng_ph = random.Random(hash(aid + str(day) + "ph"))
                    hh_b   = _hh_budget.get(hh, 0.0)
                    ptrip  = _pharmacy_trip(lat, lng, hh_b, role, rng=rng_ph)
                except Exception:
                    ptrip = None
            else:
                ptrip = None
            if ptrip and hh_b >= ptrip["cost"]:
                _hh_budget[hh] -= ptrip["cost"]
                health = min(100.0, health + 12.0)
                stress = max(0.0, stress - 5.0)
                store_lat_out = ptrip["store"]["lat"]
                store_lng_out = ptrip["store"]["lng"]
                activity = "Pharmacy"
                events_out.append({
                    "label":     ptrip["event_label"],
                    "icon":      "💊",
                    "tone":      "warn",
                    "agentName": name,
                    "district":  district,
                    "agentId":   aid,
                    "store_lat": store_lat_out,
                    "store_lng": store_lng_out,
                })

        # ── Derive this agent's budget from household share ───────────────────
        share  = BUDGET_SHARE.get(role, 1.0)
        budget = round(_hh_budget.get(hh, 0.0) * share) if share > 0 else 0

        out = {
            "id":       aid,
            "stress":   round(min(100.0, max(0.0, stress)), 1),
            "budget":   budget,
            "activity": activity,
            "_hunger":  round(min(100.0, max(0.0, hunger)), 2),
            "_fun":     round(min(100.0, max(0.0, fun)),    2),
            "_health":  round(min(100.0, max(0.0, health)), 2),
        }
        if activity in ("Shopping", "Pharmacy") and store_lat_out is not None:
            out["store_lat"] = store_lat_out
            out["store_lng"] = store_lng_out
        agents_out.append(out)

    return {
        "agents":     agents_out,
        "events":     events_out[:15],   # cap at 15 per tick
        "sim_time":   _sim_time.strftime("%Y-%m-%d %H:%M"),
        "step_count": _step,
    }


# ─── HTTP handler ─────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass   # suppress per-request console noise

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            self._json({
                "sim_time":   _sim_time.strftime("%Y-%m-%d %H:%M"),
                "step_count": _step,
                "status":     "ready",
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/step":
            length  = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            try:
                result = step_simulation(payload.get("agents", []))
                self._json(result)
            except Exception as exc:
                print(f"[SIM API ERROR] {exc}", flush=True)
                self._json({"error": str(exc)}, 500)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    port   = int(sys.argv[1]) if len(sys.argv) > 1 else 3001
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"[SIM API] FamilySim running on port {port}", flush=True)
    sys.stdout.flush()
    server.serve_forever()
