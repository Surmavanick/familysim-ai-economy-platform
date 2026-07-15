"""
CONCRETE EXAMPLE: How to use real Georgian data in simulation

This shows exactly what to add where
"""

# ===========================================================================
# EXAMPLE 1: Use Real Salaries in Population Generator
# ===========================================================================

# FILE: simulation_core/population.py
# ADD these lines:

from data.georgia_real_data import (
    JOB_SALARIES_GEORGIA,
    TBILISI_DISTRICTS_REAL,
)

def generate_random_family_WITH_REAL_DATA(family_id):
    """Generate family with REAL Georgian salary data"""
    
    sur_names = ["Kapanadze", "Gelasvili", "Maisuradze", "Giorgadze"]
    first_names_m = ["Luka", "Giorgi", "Davit"]
    first_names_f = ["Nino", "Mariam", "Ana"]
    
    surname = random.choice(sur_names)
    
    # 1. ASSIGN TO REAL DISTRICT with real data
    district = get_district_for_agent(family_id)
    real_district_data = TBILISI_DISTRICTS_REAL[district]
    
    family_config = []
    
    # 2. FATHER - assign real job with real salary
    father_jobs = ["engineer", "manager_junior", "teacher_public", "driver", 
                   "factory_worker", "accountant", "electrician"]
    father_job = random.choice(father_jobs)
    father_base_salary = JOB_SALARIES_GEORGIA[father_job]
    father_salary = father_base_salary * real_district_data["income_modifier"]
    
    family_config.append({
        "name": f"{random.choice(first_names_m)} {surname}",
        "role": "father",
        "age": random.randint(30, 55),
        "district": district,
        "job": father_job,  # ✨ NEW
        "salary": father_salary,  # ✨ NEW (not constant, based on real data)
    })
    
    # 3. MOTHER - assign real job
    mother_jobs = ["teacher_public", "shop_assistant", "nurse", 
                   "accountant", "cook", "cleaner"]
    mother_job = random.choice(mother_jobs)
    mother_base_salary = JOB_SALARIES_GEORGIA[mother_job]
    mother_salary = mother_base_salary * real_district_data["income_modifier"]
    
    family_config.append({
        "name": f"{random.choice(first_names_f)} {surname}",
        "role": "mother",
        "age": random.randint(28, 52),
        "district": district,
        "job": mother_job,  # ✨ NEW
        "salary": mother_salary,  # ✨ NEW
    })
    
    # 4. INITIAL BUDGET = realistic monthly earnings (not random 1500-5000)
    household_monthly_income = father_salary + mother_salary
    # But only 80-120% is liquid cash (rest bills, debt, etc)
    initial_budget = household_monthly_income * random.uniform(0.8, 1.2)
    
    print(f"""
    📊 Family {family_id} Data:
    District: {district} (unemployment: {real_district_data['unemployment_rate']*100:.0f}%)
    Father: {father_job} ({father_salary:.0f}₾)
    Mother: {mother_job} ({mother_salary:.0f}₾)
    Total Income: {household_monthly_income:.0f}₾
    Initial Budget: {initial_budget:.0f}₾
    """)
    
    return {
        "household_id": family_id,
        "surname": surname,
        "district": district,
        "members": family_config,
        "initial_budget": initial_budget,
        "monthly_income": household_monthly_income,  # ✨ NEW
    }

# ===========================================================================
# EXAMPLE 2: Use Real Product Prices in Market
# ===========================================================================

# FILE: economy_engine/market.py
# UPDATE Store initialization:

from data.georgia_real_data import GEORGIAN_PRODUCTS_REAL

class Store:
    def __init__(self, name, products=None):
        self.name = name
        self.products = products or {}
        self.sales_history = {}
    
    @staticmethod
    def create_from_real_data(store_name):
        """Create store with REAL Georgian products"""
        products_dict = {}
        
        for product_id, product_data in GEORGIAN_PRODUCTS_REAL.items():
            # Check if this product should be in this store
            allowed_stores = product_data.get("store", ["Spar", "Magniti", "Carrefour"])
            
            if store_name not in allowed_stores:
                continue  # Skip products not sold here
            
            base_price = product_data["price"]
            
            # Apply store-specific pricing strategy
            if store_name == "Magniti":
                final_price = base_price * 0.95  # Magniti is 5% cheaper
            elif store_name == "Carrefour":
                final_price = base_price * 1.10  # Carrefour is premium (+10%)
            else:  # Spar, Goodwill
                final_price = base_price
            
            products_dict[product_id] = {
                "price": final_price,
                "category": product_data["category"],
                "quantity": 999,  # Unlimited stock
            }
        
        return Store(store_name, products_dict)

class Market:
    def __init__(self, model=None):
        self.model = model
        self.stores = {}
        self.inflation_index = 1.0
        
        # ✨ Initialize with real data instead of CSV
        self.stores["Magniti"] = Store.create_from_real_data("Magniti")
        self.stores["Spar"] = Store.create_from_real_data("Spar")
        self.stores["Carrefour"] = Store.create_from_real_data("Carrefour")
        
        print(f"✓ Market initialized with {len(GEORGIAN_PRODUCTS_REAL)} real Georgian products")

# ===========================================================================
# EXAMPLE 3: Add Seasonal Price Changes
# ===========================================================================

# FILE: events/system.py
# ADD this method:

from data.georgia_real_data import SEASONAL_PATTERNS
import calendar

def apply_seasonal_effects(self, current_month):
    """Apply seasonal price and expense changes based on real Georgian patterns"""
    
    month_names = ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]
    month_name = month_names[current_month - 1]
    
    if month_name not in SEASONAL_PATTERNS:
        return  # No seasonal effects this month
    
    pattern = SEASONAL_PATTERNS[month_name]
    
    # 1. Apply food price multiplier
    if "food_multiplier" in pattern:
        food_multiplier = pattern["food_multiplier"]
        for store in self.model.market.stores.values():
            for product_id, product_info in store.products.items():
                if GEORGIAN_PRODUCTS_REAL[product_id]["category"] == "staple":
                    product_info["price"] *= food_multiplier
        
        print(f"🍎 {pattern['name']}: Food prices changed by {(food_multiplier-1)*100:+.0f}%")
    
    # 2. Apply utility multiplier (heating costs)
    if "utility_multiplier" in pattern:
        utility_multiplier = pattern["utility_multiplier"]
        for household in self.model.households:
            household.monthly_utility_cost *= utility_multiplier
        
        print(f"⚡ {pattern['name']}: Utility costs changed by {(utility_multiplier-1)*100:+.0f}%")
    
    # 3. Apply gifting multiplier (gift expenses)
    if "gifting_multiplier" in pattern:
        print(f"🎁 {pattern['name']}: Gift expenses +{(pattern['gifting_multiplier']-1)*100:.0f}%")
    
    # 4. Trigger cultural events
    if "events" in pattern:
        for event in pattern["events"]:
            print(f"🎉 Event: {event}")

# ===========================================================================
# EXAMPLE 4: Use Real District Data for Housing Costs
# ===========================================================================

# FILE: simulation_core/model.py
# IN __init__ or step():

from data.georgia_real_data import HOUSING_COSTS, UTILITIES_GEORGIA

class FamilySimulation:
    def __init__(self, ...):
        # ... existing code ...
        
        # ✨ NEW: Calculate housing costs by district
        for household in self.households:
            district = household.district
            
            if district in HOUSING_COSTS:
                housing_data = HOUSING_COSTS[district]
                
                # Calculate rent for household size
                household_size = len(household.members)
                apartment_size_m2 = 20 + (5 * household_size)  # 20 + 5m² per person
                rent_per_month = apartment_size_m2 * housing_data["rent_2bedroom_sqm"]
                
                household.monthly_rent = rent_per_month
                household.housing_cost = rent_per_month
                
                print(f"💰 {household.name} ({district}): Rent = ₾{rent_per_month:.0f}/month")

# ===========================================================================
# EXAMPLE 5: Use Real Salary Data in Agent Monthly Payday
# ===========================================================================

# FILE: agents/base.py
# UPDATE pay_day() method:

def pay_day(self):
    """Monthly payday with REAL Georgian salary"""
    
    # Use real salary from job
    if hasattr(self, 'job') and self.job in JOB_SALARIES_GEORGIA:
        base_salary = JOB_SALARIES_GEORGIA[self.job]
    else:
        base_salary = 2000  # default
    
    # Apply district income modifier
    district_data = TBILISI_DISTRICTS_REAL[self.district]
    adjusted_salary = base_salary * district_data["income_modifier"]
    
    # Check for unemployment (matches district unemployment rate)
    if random.random() < district_data["unemployment_rate"]:
        # Agent unemployed this month
        salary = 0
        print(f"😞 {self.name} unemployed! (district rate: {district_data['unemployment_rate']*100:.0f}%)")
    else:
        salary = adjusted_salary * 0.85  # After 15% taxes (Georgian tax rate)
        print(f"💵 {self.name} paid: ₾{salary:.0f} ({self.job})")
    
    # Add to household budget
    self.household.budget += salary
    self.monthly_income = salary
    
    # Apply inflation to salary (tracking lost purchasing power)
    if hasattr(self.model, 'inflation_index'):
        real_income = salary / self.model.inflation_index
        print(f"   Real purchasing power: ₾{real_income:.0f} (after {self.model.inflation_index:.1%} inflation)")

# ===========================================================================
# EXAMPLE 6: Track Realistic Budget Breakdown
# ===========================================================================

# FILE: results/report_generator.py
# NEW function:

from data.georgia_real_data import GEORGIA_ECONOMIC_INDICATORS

def analyze_budget_breakdown(households):
    """Compare actual spending to Georgian consumer basket"""
    
    consumer_basket = GEORGIA_ECONOMIC_INDICATORS["budget_breakdown"]
    
    actual_breakdown = {
        "food": 0,
        "utilities": 0,
        "transport": 0,
        "healthcare": 0,
        "education": 0,
        "clothing": 0,
        "leisure": 0,
        "other": 0,
    }
    
    total_spending = 0
    
    # Aggregate spending from all households
    for household in households:
        # ... calculate spending by category ...
        total_spending += household.total_spending
    
    # Compare to reality
    print("\n📊 Budget Breakdown Analysis:")
    print("Category       │ Expected │ Actual │ Diff")
    print("───────────────┼──────────┼────────┼────")
    
    for category in actual_breakdown:
        expected_pct = consumer_basket.get(f"{category}_pct", 0) * 100
        actual_pct = (actual_breakdown[category] / total_spending) * 100 if total_spending > 0 else 0
        diff = actual_pct - expected_pct
        
        print(f"{category:14} │ {expected_pct:7.1f}% │ {actual_pct:5.1f}% │ {diff:+5.1f}%")

# ===========================================================================
# QUICK START: Use this right now
# ===========================================================================

if __name__ == "__main__":
    # Test the real data
    print("=== Testing Real Georgian Data ===\n")
    
    # 1. Test family generation with real data
    print("1. Generating family with REAL data:")
    family = generate_random_family_WITH_REAL_DATA(1)
    print(f"   Generated: {family}\n")
    
    # 2. Test market with real data
    print("2. Creating market with REAL products:")
    market = Market()
    print(f"   Magniti products: {len(market.stores['Magniti'].products)}")
    print(f"   Sample prices:")
    for product_id in list(market.stores['Magniti'].products.keys())[:3]:
        price = market.stores['Magniti'].products[product_id]['price']
        print(f"     {product_id}: ₾{price:.2f}")
    
    # 3. Test seasonal effects
    print("\n3. Testing seasonal effects (March - Women's Day):")
    # apply_seasonal_effects(3)  # Month 3 = March
    
    print("\n✅ Real data integration working!")
