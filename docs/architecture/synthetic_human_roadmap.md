# 🧬 Synthetic Human Simulation - Implementation Roadmap

## Vision
Transform from **Homo Economicus** (rational economic actor) → **Synthetic Human** (emotional, social, cultural)

---

## Phase 1: Emotional System (Week 1)
### Goal: Agents have feelings, not just budgets

#### 1.1 Add Emotional Profile to Agent
```python
# In agents/base.py __init__():

from agents.life_simulation import EmotionalProfile

self.emotions = EmotionalProfile()
# Tracks: stress, happiness, boredom, fatigue, jealousy, shame, attachment
```

#### 1.2 Update Emotions During Daily Cycle
```python
# In agents/base.py step():

# Currently: nothing happens with emotions
# Add: emotions change based on activities

if current_hour == 9:  # Work starts
    self.emotions.stress += 5
    self.emotions.fatigue += 3

if current_hour == 20:  # Evening with family
    self.emotions.happiness += 10
    self.emotions.stress -= 5
```

#### 1.3 Modify Decision-Making Based on Emotion
```python
# Before: 
if budget > shopping_cost:
    buy_cheapest()

# After:
if self.emotions.stress > 70:
    buy_comfort_items()  # Stress shopping
elif self.emotions.boredom > 75:
    buy_entertainment()  # Boredom relief
else:
    optimize_budget()  # Normal shopping
```

#### 1.4 Test: Run 30-day simulation
- Expected: Agents with high stress buy more
- Expected: Agents with low happiness seek social activities
- Output: `simulation_report.json` includes emotion metrics

**Validation**: 
```
✅ Emotional trajectory visible in output
✅ Stress peaks around payday pressure period
✅ Happiness increases on weekends
```

---

## Phase 2: Daily Life Routine (Week 2)
### Goal: Agents follow realistic daily schedules

#### 2.1 Implement LifeRoutineEngine
```python
# Already created in agents/life_simulation.py
# Now integrate into agent:

from agents.life_simulation import LifeRoutineEngine

self.daily_routine = LifeRoutineEngine(self)

# In step():
current_hour = self.model.schedule.steps % 24
activity, enjoyment = self.daily_routine.get_activity_for_hour(
    current_hour, 
    self.model.schedule.steps % 7  # day of week
)
```

#### 2.2 Map Activities to Hours
```
00-06: SLEEP
07-08: BREAKFAST (family time, enjoyment: 0.6)
09-17: WORK/SCHOOL (depending on age, enjoyment: 0.3-0.4)
12-13: LUNCH (enjoyment: 0.5)
18-19: DINNER (family ritual, enjoyment: 0.7)
20-22: LEISURE (enjoyment: 0.5-0.7)
23:    SLEEP
```

#### 2.3 Activities Affect Emotions
```python
# In LifeRoutineEngine.update_emotions_from_activity():

if activity == "WORK":
    stress += 5
    fatigue += 10

if activity == "SOCIALIZING":
    happiness += 15
    boredom -= 20
    stress -= 5

if activity == "SLEEP":
    fatigue -= 15
    stress -= 5
```

#### 2.4 Test: Run 30-day simulation
- Expected: Daily patterns visible (sleep at night, work during day)
- Expected: Stress accumulates during work week, drops on weekends
- Expected: Agents are tired (fatigue > 50) in mornings, rested after sleep

**Validation**:
```
✅ Hourly activity logging shows realistic patterns
✅ Fatigue curve: high in evening, low after sleep
✅ Stress drops on weekends
```

---

## Phase 3: Identity Filters (Week 3)
### Goal: Same situation → different agents act differently

#### 3.1 Create Identity Classes
```python
# Already in agents/life_simulation.py
# Add to agent:

from agents.life_simulation import Identity, GEORGIAN_ARCHETYPES

archetype = random.choice(list(GEORGIAN_ARCHETYPES.keys()))
self.identity = Identity(
    archetype=archetype,
    risk_aversion=random.uniform(0.3, 0.9),
    materialism=random.uniform(0.2, 0.8),
    sociability=random.uniform(0.3, 0.9),
    tradition_adherence=random.uniform(0.2, 0.9),
)
```

#### 3.2 Implement Identity-Based Decisions
```python
def _decide_action_based_on_identity(self, activity):
    """Different agents make different choices"""
    
    if activity == "EATING":
        if self.identity.archetype == "health_conscious_mother":
            return "buy_organic_food"  # 20% more expensive
        elif self.identity.archetype == "status_seeking_young":
            return "go_to_expensive_cafe"
        elif self.identity.archetype == "traditional_grandfather":
            return "buy_georgian_traditional"
        else:
            return "buy_cheapest"
    
    if activity == "SHOPPING":
        if self.identity.materialism > 0.8:
            self._buy_status_items()  # Brand shopping
        elif self.identity.tradition_adherence > 0.8:
            self._buy_traditional_items()
        else:
            self._budget_optimize()
```

#### 3.3 Identity Affects Stress Response
```python
# Different personalities handle stress differently

if self.emotions.stress > 70:
    if self.identity.risk_aversion > 0.7:
        # Conservative: save money, reduce spending
        self.household.budget_reserve += 100
    else:
        # Risk-taker: go shopping, spend on leisure
        self._impulse_buy()
```

#### 3.4 Test: Run 30-day simulation
- Expected: Health-conscious mothers buy organic (higher expenses)
- Expected: Status seekers have visible branded purchases
- Expected: Traditional agents enforce family spending
- Track: Budget breakdown by archetype

**Validation**:
```
✅ health_conscious_mother: 20% more on food
✅ status_seeking_young: 30% more on brands
✅ traditional_grandfather: forces supra spending
```

---

## Phase 4: Habits System (Week 4)
### Goal: Agents act irrationally (like real humans)

#### 4.1 Create Habit Database
```python
# In agents/life_simulation.py

COMMON_HABITS = [
    Habit("expensive_coffee", "daily", cost=3, relief=0.6, irrationality=0.8),
    Habit("stress_eating", "random", cost=5, relief=0.7, irrationality=0.9),
    Habit("brand_loyalty", "weekly", cost=0, relief=0.3, irrationality=0.7),
    Habit("tiktok_scrolling", "daily", cost=0, relief=0.5, irrationality=0.5),
    Habit("social_media_shopping", "random", cost=50, relief=0.2, irrationality=0.95),
]
```

#### 4.2 Assign Habits to Agents
```python
def __init__(self):
    # Each agent gets 2-4 habits
    habit_count = random.randint(2, 4)
    self.habits = random.sample(COMMON_HABITS, habit_count)
```

#### 4.3 Execute Habits Instead of Optimization
```python
def _decide_action_based_on_emotion(self):
    """30% chance to follow habit instead of optimize"""
    
    if random.random() < 0.3:  # HABIT decision
        habit = random.choice(self.habits)
        
        if habit.cost > 0 and self.household.budget >= habit.cost:
            self.household.budget -= habit.cost
            self.emotions.stress -= habit.relief * 20
            self.emotions.boredom -= habit.relief * 15
            print(f"💭 {self.name} acted on habit: {habit.name}")
        
        return  # Don't optimize economy
    
    # Otherwise: normal economic decision
    self._optimize_budget()
```

#### 4.4 Test: Run 30-day simulation
- Expected: Some agents waste money on coffee despite low budget
- Expected: Stress-eating visible when stress is high
- Expected: Brand loyalty prevents switching to cheaper stores
- Track: Irrational spending % by agent

**Validation**:
```
✅ Agents spend ₾3-5 on coffee daily (inefficiency visible)
✅ Stress-eating increases when stress > 70
✅ Brand loyalty prevents optimal shopping
```

---

## Phase 5: Social Influence (Week 5)
### Goal: Neighbors affect each other's behavior

#### 5.1 Create SocialInfluenceEngine
```python
# In simulation_core/model.py __init__():

from agents.life_simulation import SocialInfluenceEngine

self.social_engine = SocialInfluenceEngine(self)
```

#### 5.2 Gossip About Stores
```python
def _receive_social_influence(self):
    """Evening (20:00) agents chat with neighbors"""
    
    if self.model.schedule.steps % 24 == 20:  # Evening
        neighbors = self._get_household_neighbors(n=2)
        
        for neighbor in neighbors:
            if random.random() < 0.3:  # 30% chance to share
                best_store = neighbor._get_best_store_for_budget()
                self.store_loyalty[best_store] += 0.2
                print(f"💬 {neighbor.name} → {self.name}: '{best_store} has good prices!'")
```

#### 5.3 Trend Propagation
```python
def _spread_trends(self):
    """If one agent likes product, neighbors like it too"""
    
    if self.emotions.happiness > 80:  # Happy agent
        neighbors = self._get_household_neighbors(n=3)
        
        for neighbor in neighbors:
            # "Try this snack!" = neighbor wants it too
            product = random.choice(self.recent_purchases)
            neighbor.product_interest[product] += 0.3
            print(f"📱 Trend: {product} spreads from {self.name} to {neighbor.name}")
```

#### 5.4 Aspiration Contagion
```python
def _spread_aspirations(self):
    """If neighbor buys car, I want car too"""
    
    if any(aspiration.name == "buy_car" for aspiration in self.aspirations):
        neighbors = self._get_household_neighbors(n=2)
        
        for neighbor in neighbors:
            if not any(a.name == "buy_car" for a in neighbor.aspirations):
                neighbor.aspirations.append(
                    Aspiration(name="buy_car", priority=0.6, ...)
                )
                print(f"🎯 {self.name} influenced {neighbor.name}: 'I want car too!'")
```

#### 5.5 Test: Run 30-day simulation
- Expected: All agents gradually prefer same store (recommendation spread)
- Expected: Trends visible (everyone buys same snack)
- Expected: Aspirations propagate through neighborhood
- Track: Network effects on store preference

**Validation**:
```
✅ Store preference change: before 40/30/30 → after 60/25/15
✅ Product trends: 1 agent → 5 agents in 2 weeks
✅ Car aspiration spreads to 3 neighboring families
```

---

## Phase 6: Cultural System (Week 6)
### Goal: Georgian culture drives realistic behavior

#### 6.1 Create CultureEngine
```python
# In simulation_core/model.py __init__():

from agents.life_simulation import CultureEngine

self.culture_engine = CultureEngine()
```

#### 6.2 Implement Georgian Holidays
```python
def check_upcoming_obligation(self, month: int, day: int):
    """Check for cultural obligations"""
    
    holidays = {
        (1, 1): "New Year",
        (3, 8): "Women's Day",
        (5, 9): "Victory Day",
        (10, 14): "Svetitskoba",
        (11, 26): "Independence Day",
    }
    
    if (month, day) in holidays:
        return holidays[(month, day)]
    
    return None
```

#### 6.3 Enforce Supra Obligations
```python
def apply_supra_obligation(self, family_visiting: bool = False):
    """Supra = family feast = must do ~100-300₾"""
    
    supra_cost = random.uniform(100, 300)
    
    # EVEN IF POOR: you host supra for family
    if self.household.budget >= supra_cost or family_visiting:
        self.household.budget -= supra_cost
        self.emotions.happiness += 20
        self.emotions.stress -= 10
        print(f"🍽️ {self.name} hosted supra (₾{supra_cost:.0f})")
        return True
    else:
        # Can't afford supra = SHAME
        self.emotions.shame += 15
        print(f"😞 {self.name} couldn't afford supra - shame!")
        return False
```

#### 6.4 Implement Cultural Foods
```python
# Georgian products that agents prefer

GEORGIAN_PREFERENCE = {
    "khachapuri": 0.9,   # Everyone loves, buy even when expensive
    "cheese": 0.85,
    "bread": 0.9,
    "wine": 0.8,
    "chacha": 0.7,
}

# When shopping, traditional agents prioritize Georgian foods
if self.identity.tradition_adherence > 0.7:
    for product, preference in GEORGIAN_PREFERENCE.items():
        if preference > 0.8:
            self._buy_product(product)  # Higher budget allocation
```

#### 6.5 Test: Run 30-day simulation
- Expected: Jan 1, Mar 8, May 9, Oct 14, Nov 26 = spending spikes
- Expected: Supra happens even for poor families (or shame increases)
- Expected: Georgian food preference shifts budget allocation
- Track: Holiday-driven expenses

**Validation**:
```
✅ Jan 1 spending spike: average budget -200₾
✅ Women's Day: gifts purchased (Mar 1-10)
✅ Supra obligation enforced: poor families take shame penalty
✅ Georgian foods: 40% of food budget vs 20% before
```

---

## Phase 7: Integration & Testing (Week 7)
### Goal: All systems work together

#### 7.1 Update agents/base.py
```python
def step(self):
    """Enhanced synthetic human step"""
    
    # 1. Daily activity
    current_hour = self.model.schedule.steps % 24
    activity, enjoyment = self.daily_routine.get_activity_for_hour(current_hour)
    
    # 2. Emotions from activity
    self.daily_routine.update_emotions_from_activity(activity, enjoyment)
    
    # 3. Identity filter
    decision = self._decide_action_based_on_identity(activity)
    
    # 4. Habits vs optimization
    if self._should_act_on_habit():
        self._execute_habit()
    
    # 5. Social influence
    self._receive_social_influence()
    
    # 6. Cultural obligations
    if self.model.culture_engine.check_upcoming_obligation(...):
        self.model.culture_engine.apply_supra_obligation(self)
    
    # 7. Economic decisions
    if activity == "SHOPPING":
        self._make_shopping_decision()
    
    # 8. Sparse LLM reasoning
    if self.emotions.stress > 75 and random.random() < 0.1:
        self._think_with_llm()
```

#### 7.2 Update simulation_core/model.py
```python
def __init__(self):
    # Existing code...
    self.market = Market(...)
    self.llm = LocalLLMInterface()
    
    # NEW: Life simulation engines
    self.social_engine = SocialInfluenceEngine(self)
    self.culture_engine = CultureEngine()
```

#### 7.3 Update simulation report
```python
# In results/report_generator.py

def generate_simulation_report():
    """Include emotional and social metrics"""
    
    report = {
        "metadata": {...},
        
        # Economic (existing)
        "economic_summary": {...},
        
        # NEW: Emotional metrics
        "emotional_summary": {
            "average_stress": np.mean([a.emotions.stress for a in agents]),
            "average_happiness": np.mean([a.emotions.happiness for a in agents]),
            "stress_trajectory": [...],  # Over 30 days
        },
        
        # NEW: Social metrics
        "social_summary": {
            "store_gossip_events": count_gossip,
            "trend_spread": [{product: count}],
            "aspiration_contagion": {...},
        },
        
        # NEW: Cultural metrics
        "cultural_summary": {
            "supra_events": count,
            "georgian_food_budget_pct": pct,
            "holiday_compliance": {...},
        },
        
        # NEW: Identity breakdown
        "archetype_breakdown": {
            "health_conscious_mother": count,
            "status_seeking_young": count,
            ...
        },
    }
```

#### 7.4 Run Full Integration Test
```bash
python3 simulation_run.py
```

**Expected Output**:
```
Day 1:
  👨‍👩‍👧‍👦 Family: Giorgi (Father), Natia (Mother), Luka (Son)
  📍 District: Saburtalo (wealthy)
  💼 Giorgi works: stress 45 → 52
  🏫 Luka at school: enjoyment 0.4, stress 35
  🛒 Natia shopping: buys organic (health_conscious)
  💭 Giorgi: "stressed, might buy coffee"
  💬 Chat with neighbor about Magniti prices

Day 2-7:
  📊 Emotional trajectory visible
  🎯 Natia influences 2 neighbors: organic food
  📈 Store gossip affecting shopping patterns

Day 14:
  🍽️ SUPRA OBLIGATION (Women's Day prep)
  💰 Average spending +250₾
  😊 Happiness spike after event

Day 30:
  📊 Report shows:
  - Stress curve: peaks (work week), dips (weekend)
  - Social network: who influenced whom
  - Cultural impact: supra/holiday spending
  - Identity patterns: archetypes visible
  - Emergence: unexpected behaviors
```

---

## Phase 8: Refinement & Polish (Week 8)
### Goal: Make it production-ready

#### 8.1 Performance Optimization
- Add caching for social lookups
- Batch emotion updates
- Profile LLM calls

#### 8.2 Visualization
```python
# Optional: Create visualization
# - Daily stress curve
# - Social network graph
# - Spending by archetype
# - Store preference heatmap
```

#### 8.3 Validation Metrics
```python
# Measure emergence quality:
behaviors_that_are_irrational = count  # Should be high
budgets_that_converge_to_optimal = count  # Should be low
social_influence_events = count  # Should be visible
cultural_compliance = pct  # Should be >80%
identity_coherence = measure()  # Health-conscious doesn't buy junk
```

---

## Success Criteria

### Phase 1-4 (Weeks 1-4)
```
✅ Agents have emotions that affect decisions
✅ Daily routines visible (sleep, work, leisure patterns)
✅ Same situation → different agents act differently
✅ Irrational spending visible in output
```

### Phase 5-6 (Weeks 5-6)
```
✅ Social influence propagates through neighborhood
✅ Cultural obligations override budget optimization
✅ Supra events happen despite poverty
✅ Georgian food preference visible
```

### Phase 7-8 (Weeks 7-8)
```
✅ All systems integrated and working together
✅ Report shows emotional + social + cultural metrics
✅ Emergent behaviors visible (not pre-programmed)
✅ Simulation feels "alive" - not just economic calculator
```

---

## Key Principles Throughout

1. **Irrationality is a feature**: Agents should NOT always optimize
2. **Identity drives behavior**: Same person always acts similar
3. **Social pressure matters**: Neighbors influence decisions
4. **Culture overrides economy**: Supra > budget optimization
5. **Emergence over prescription**: Let behaviors emerge, don't hard-code them
6. **Emotions are first-class**: Not afterthought, but core decision driver

---

## Timeline

```
Week 1: Emotions ✓
Week 2: Daily Routines ✓
Week 3: Identity ✓
Week 4: Habits ✓
Week 5: Social Influence ✓
Week 6: Cultural System ✓
Week 7: Full Integration ✓
Week 8: Polish & Deploy ✓

= 2 months to synthetic human simulation ready
```

---

## Expected Results Transformation

### Before (Homo Economicus)
```
Budget: ₾3,961
Stress: 50.3
Events: 4

Why boring?: Everyone optimizes identically
```

### After (Synthetic Humans)
```
Budget: ₾2,800 (varies wildly by archetype)
Stress: Complex trajectory (work week peak, weekend dip)
Happiness: Visible from relationships & culture
Social Network: Gossip chains visible
Identity Patterns: Health-conscious ≠ Status-seeker spending
Emergence: Unexpected: neighborhood goes vegan trend
Cultural: Supra events override all economics
```

---

## მხარდამჭერი ფაილები (Supporting Files)

- [ ] `agents/life_simulation.py` - ✅ Created
- [ ] `INTEGRATION_ROADMAP.txt` - ✅ Created
- [ ] `agents/base.py` - 📝 To modify
- [ ] `simulation_core/model.py` - 📝 To modify
- [ ] `results/report_generator.py` - 📝 To enhance
- [ ] `SYNTHETIC_HUMAN_ROADMAP.md` - ✅ This file

---

## რომელია დასწაფვის შემდეგი ნაბიჯი?

**ახლა გაქვთ სამი ვარიანტი:**

1. **დაწერეთ Phase 1** (Emotions) - 3-4 საათი
   - Quick win, tangible results
   - უნდა დაინტეგრიროთ EmotionalProfile-ი
   - გაიქ simulation, დაინახოთ ცვლილებები
   
2. **დაწერეთ Phase 3** (Identity) - 2-3 საათი
   - More dramatic behavioral differences
   - მაშინვე ჩანდება results
   
3. **პირველი მთელი run** - დაიწყოთ Phase 1-ით

---

**რომელი სიმულაციის version გაინტერესებთ პირველ რიგში?**
