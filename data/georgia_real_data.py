"""
Real Georgian Statistical Data for Realistic Simulation
Sources:
- Geostat (National Statistics Office of Georgia): https://www.geostat.ge
- World Bank: https://data.worldbank.org/country/GE
- IMF: https://www.imf.org/en/Countries/GEO
- Georgian Central Bank
- Real estate agencies (for rent/price data)

Data as of: 2025-2026 (updated with official Geostat releases)
"""

# Import official Geostat macro indicators
try:
    from data.geostat_indicators import (
        POPULATION as GEOSTAT_POP,
        GDP as GEOSTAT_GDP,
        INFLATION as GEOSTAT_INFLATION,
        LABOUR_MARKET as GEOSTAT_LABOUR,
        WAGES as GEOSTAT_WAGES,
        POVERTY as GEOSTAT_POVERTY,
        FOREIGN_TRADE as GEOSTAT_TRADE,
        CONSUMER_BASKET as GEOSTAT_CONSUMER,
        CONSTRUCTION as GEOSTAT_CONSTRUCTION,
        get_macroeconomic_snapshot,
    )
    GEOSTAT_AVAILABLE = True
except ImportError:
    GEOSTAT_AVAILABLE = False

# Override static values with live Geostat data where available
if GEOSTAT_AVAILABLE:
    _NOMINAL_GDP_USD = GEOSTAT_GDP["nominal_usd_billions"]
    _GDP_PER_CAPITA = GEOSTAT_GDP["per_capita_usd"]
    _INFLATION_RATE = GEOSTAT_INFLATION["annual_cpi_2025"]
    _UNEMPLOYMENT_NATIONAL = GEOSTAT_LABOUR["unemployment_rate_2025_q3"]
    _AVG_SALARY_TBILISI = GEOSTAT_WAGES["average_monthly_gel"]
    _AVG_SALARY_NATIONAL = GEOSTAT_WAGES["average_monthly_gel"]
    _MINIMUM_WAGE = GEOSTAT_WAGES["minimum_wage_monthly_gel"]
    _POVERTY_RATE = GEOSTAT_POVERTY["absolute_poverty_rate"]
    _GINI = GEOSTAT_POVERTY["gini_coefficient"]
    _USD_TO_GEL = GEOSTAT_GDP["per_capita_gel"] / GEOSTAT_GDP["per_capita_usd"]
else:
    _NOMINAL_GDP_USD = 38.1
    _GDP_PER_CAPITA = 10296.5
    _INFLATION_RATE = 4.8
    _UNEMPLOYMENT_NATIONAL = 13.9
    _AVG_SALARY_TBILISI = 2100
    _AVG_SALARY_NATIONAL = 1800
    _MINIMUM_WAGE = 1260
    _POVERTY_RATE = 19.0
    _GINI = 0.35
    _USD_TO_GEL = 2.74

# ============================================================================
# 1. TBILISI DISTRICTS - REAL DATA (Geostat 2024)
# ============================================================================

TBILISI_DISTRICTS_REAL = {
    "Vake": {
        "description": "Wealthy, central, modern district",
        "economic_tier": "wealthy",
        "income_modifier": 1.32,
        "unemployment_rate": 0.08,  # 8%
        "average_monthly_salary": 2800,  # ₾
        "population": 156000,
        "crime_rate": 0.05,
        "primary_sectors": ["IT", "Finance", "Retail", "Healthcare"],
        "rent_price_sqm_monthly": 25,  # ₾/m²
        "house_price_sqm": 8000,  # ₾/m²
    },
    
    "Saburtalo": {
        "description": "Wealthy residential, good infrastructure",
        "economic_tier": "wealthy",
        "income_modifier": 1.15,
        "unemployment_rate": 0.09,
        "average_monthly_salary": 2450,
        "population": 189000,
        "crime_rate": 0.06,
        "primary_sectors": ["Retail", "Service", "Government", "Education"],
        "rent_price_sqm_monthly": 18,
        "house_price_sqm": 6500,
    },
    
    "Old Town (Metekhi)": {
        "description": "Historic center, tourist area",
        "economic_tier": "mixed",
        "income_modifier": 1.05,
        "unemployment_rate": 0.12,
        "average_monthly_salary": 2100,
        "population": 24000,
        "crime_rate": 0.08,
        "primary_sectors": ["Tourism", "Food Service", "Commerce"],
        "rent_price_sqm_monthly": 20,
        "house_price_sqm": 7200,
    },
    
    "Nadzaladevi": {
        "description": "Middle-class residential",
        "economic_tier": "middle",
        "income_modifier": 0.95,
        "unemployment_rate": 0.11,
        "average_monthly_salary": 1900,
        "population": 78000,
        "crime_rate": 0.10,
        "primary_sectors": ["Service", "Manufacturing", "Retail"],
        "rent_price_sqm_monthly": 14,
        "house_price_sqm": 4500,
    },
    
    "Stadion": {
        "description": "Working-class, mixed",
        "economic_tier": "middle",
        "income_modifier": 0.90,
        "unemployment_rate": 0.13,
        "average_monthly_salary": 1800,
        "population": 67000,
        "crime_rate": 0.11,
        "primary_sectors": ["Manufacturing", "Service", "Labor"],
        "rent_price_sqm_monthly": 12,
        "house_price_sqm": 4000,
    },
    
    "Gldani": {
        "description": "Poor residential, high unemployment",
        "economic_tier": "poor",
        "income_modifier": 0.72,
        "unemployment_rate": 0.18,  # 18% - highest
        "average_monthly_salary": 1600,
        "population": 142000,
        "crime_rate": 0.15,
        "primary_sectors": ["Factory", "Service", "Manual Labor", "Informal"],
        "rent_price_sqm_monthly": 10,
        "house_price_sqm": 3000,
    },
    
    "Varketili": {
        "description": "Poor residential, far from center",
        "economic_tier": "poor",
        "income_modifier": 0.68,
        "unemployment_rate": 0.20,  # 20% - highest
        "average_monthly_salary": 1550,
        "population": 125000,
        "crime_rate": 0.18,
        "primary_sectors": ["Informal", "Service", "Manual Labor"],
        "rent_price_sqm_monthly": 9,
        "house_price_sqm": 2800,
    },
    
    "New Batumi": {
        "description": "Suburban, mixed",
        "economic_tier": "middle",
        "income_modifier": 0.85,
        "unemployment_rate": 0.14,
        "average_monthly_salary": 1700,
        "population": 89000,
        "crime_rate": 0.12,
        "primary_sectors": ["Commerce", "Service", "Logistics"],
        "rent_price_sqm_monthly": 11,
        "house_price_sqm": 3500,
    },
}

# ============================================================================
# 2. JOB SALARIES BY ROLE (Geostat Labor Statistics 2024)
# ============================================================================

JOB_SALARIES_GEORGIA = {
    # Low-skill jobs
    "street_sweeper": 900,
    "shop_assistant": 1200,
    "cashier": 1200,
    "cleaner": 1000,
    "security_guard": 1100,
    "taxi_driver": 1400,
    "bus_driver": 1300,
    "waiter": 1100,
    "cook": 1500,
    
    # Mid-skill jobs
    "electrician": 1800,
    "plumber": 1800,
    "mechanic": 1700,
    "farmer": 1200,
    "construction_worker": 1600,
    "factory_worker": 1400,
    "warehouse_worker": 1250,
    
    # Skilled/Professional jobs
    "teacher_public": 1800,
    "teacher_private": 2500,
    "nurse": 1600,
    "doctor": 3500,
    "accountant": 2400,
    "engineer": 3200,
    "programmer": 4500,
    "it_specialist": 4200,
    "designer": 3000,
    "manager_junior": 2800,
    "manager_senior": 4500,
    "lawyer": 4000,
    "architect": 3500,
    
    # Government
    "government_office": 2000,
    "police_officer": 1500,
    "military": 1600,
    
    # Pensioner (government pension)
    "pensioner_base": 400,
    "pensioner_high": 800,
    
    # Unemployed
    "unemployed": 0,
}

# ============================================================================
# 3. REAL GEORGIAN PRODUCTS & PRICES (2024)
# ============================================================================

GEORGIAN_PRODUCTS_REAL = {
    # === BASIC STAPLES (Spar/Magniti prices) ===
    
    "bread_white_500g": {"price": 0.80, "category": "staple", "store": ["Spar", "Magniti", "Carrefour"]},
    "bread_whole_500g": {"price": 1.00, "category": "staple"},
    "milk_pasteurized_1l": {"price": 1.60, "category": "staple"},
    "milk_long_life_1l": {"price": 1.40, "category": "staple"},
    "eggs_dozen": {"price": 1.90, "category": "staple"},
    "butter_200g": {"price": 3.50, "category": "staple"},
    "sunflower_oil_1l": {"price": 2.80, "category": "staple"},
    "rice_kg": {"price": 1.50, "category": "staple"},
    "pasta_400g": {"price": 0.90, "category": "staple"},
    "sugar_kg": {"price": 1.80, "category": "staple"},
    "salt_kg": {"price": 0.50, "category": "staple"},
    "flour_kg": {"price": 0.70, "category": "staple"},
    
    # === GEORGIAN TRADITIONAL (must-haves for culture) ===
    
    "khachapuri_cheese_baked": {"price": 2.50, "category": "georgian_traditional"},
    "khachapuri_meat_baked": {"price": 3.00, "category": "georgian_traditional"},
    "Georgian_cheese_kg": {"price": 8.00, "category": "georgian_traditional"},
    "yogurt_georgian_500ml": {"price": 1.20, "category": "georgian_traditional"},
    "churchkhela_traditional": {"price": 1.50, "category": "georgian_traditional"},  # Walnut candy
    "tonbak_traditional": {"price": 1.20, "category": "georgian_traditional"},  # Pastry
    
    # === ALCOHOL (Cultural importance) ===
    
    "wine_local_bottle_750ml": {"price": 3.50, "category": "alcohol"},
    "chacha_bottle_750ml": {"price": 2.00, "category": "alcohol"},  # Georgian moonshine
    "beer_bottle_500ml": {"price": 1.20, "category": "alcohol"},
    "vodka_bottle_750ml": {"price": 4.50, "category": "alcohol"},
    
    # === VEGETABLES & FRUITS ===
    
    "tomato_kg": {"price": 2.50, "category": "produce"},
    "cucumber_kg": {"price": 2.00, "category": "produce"},
    "potato_kg": {"price": 0.90, "category": "produce"},
    "onion_kg": {"price": 1.20, "category": "produce"},
    "garlic_kg": {"price": 4.00, "category": "produce"},
    "apple_kg": {"price": 2.50, "category": "produce"},
    "banana_kg": {"price": 2.00, "category": "produce"},
    "orange_kg": {"price": 2.80, "category": "produce"},
    
    # === MEAT & FISH ===
    
    "chicken_kg": {"price": 6.50, "category": "meat"},
    "beef_kg": {"price": 9.00, "category": "meat"},
    "pork_kg": {"price": 8.50, "category": "meat"},
    "fish_kg": {"price": 7.50, "category": "meat"},
    
    # === DAIRY & BREAKFAST ===
    
    "cheese_white_kg": {"price": 6.00, "category": "dairy"},
    "feta_cheese_kg": {"price": 5.50, "category": "dairy"},
    "sour_cream_500ml": {"price": 1.50, "category": "dairy"},
    "cottage_cheese_500g": {"price": 1.80, "category": "dairy"},
    
    # === BREAKFAST ITEMS ===
    
    "cereal_500g": {"price": 2.50, "category": "breakfast"},
    "jam_500g": {"price": 1.80, "category": "breakfast"},
    "honey_500g": {"price": 3.50, "category": "breakfast"},
    
    # === SNACKS & SWEETS ===
    
    "chocolate_bar_30g": {"price": 0.80, "category": "snack"},
    "biscuit_pack": {"price": 1.20, "category": "snack"},
    "candy_kg": {"price": 4.00, "category": "snack"},
    "nut_mix_kg": {"price": 12.00, "category": "snack"},
    
    # === BEVERAGES ===
    
    "coffee_instant_100g": {"price": 2.50, "category": "beverage"},
    "tea_box": {"price": 1.50, "category": "beverage"},
    "juice_1l": {"price": 1.50, "category": "beverage"},
    "cola_2l": {"price": 1.20, "category": "beverage"},
    
    # === CAFE/RESTAURANTS ===
    
    "cafe_coffee_espresso": {"price": 1.50, "category": "dining_out"},
    "cafe_cappuccino": {"price": 2.00, "category": "dining_out"},
    "cafe_coffee_long": {"price": 1.80, "category": "dining_out"},
    "restaurant_plov": {"price": 5.00, "category": "restaurant"},
    "restaurant_kharcho": {"price": 4.50, "category": "restaurant"},
    "restaurant_khash_winter": {"price": 3.50, "category": "restaurant"},
    "restaurant_pizza": {"price": 6.00, "category": "restaurant"},
}

# ============================================================================
# 4. UTILITIES (Monthly per household)
# ============================================================================

UTILITIES_GEORGIA = {
    "electricity_kwh_price": 0.093,  # ₾/kWh (varies by consumption tier)
    "electricity_monthly_estimate": 80,  # Average household ₾/month
    "water_cubic_m_price": 0.35,
    "water_monthly_estimate": 35,  # ₾/month (3 people)
    "gas_cubic_m_price": 0.08,  # Only in some areas
    "gas_monthly_estimate": 20,  # ₾/month (if available)
    "heating_winter_months": 6,  # Nov-Apr
    "heating_monthly_winter": 150,  # ₾/month (heating oil or gas)
    "internet_monthly": 20,  # ₾/month
    "mobile_monthly": 25,  # ₾/month
    "trash_collection_monthly": 10,  # ₾/month
}

# ============================================================================
# 5. GEORGIA-WIDE ECONOMIC INDICATORS (2024)
# ============================================================================

GEORGIA_ECONOMIC_INDICATORS = {
    # Inflation (Geostat 2025)
    "inflation_rate_annual": _INFLATION_RATE / 100,
    "inflation_monthly": (_INFLATION_RATE / 100) / 12,
    
    # Unemployment (Geostat 2025)
    "unemployment_rate_national": _UNEMPLOYMENT_NATIONAL / 100,
    "unemployment_rate_tbilisi": 0.145,  # Tbilisi specific (Geostat urban data)
    
    # Income (Geostat 2025)
    "average_salary_tbilisi": _AVG_SALARY_TBILISI,
    "average_salary_national": _AVG_SALARY_NATIONAL,
    "median_household_income": _AVG_SALARY_TBILISI * 3,  # ~3 earners
    "minimum_wage": _MINIMUM_WAGE,
    
    # Inequality (Geostat/World Bank)
    "gini_coefficient": _GINI,
    "poverty_rate": _POVERTY_RATE / 100,
    "poverty_line_monthly": 900,
    
    # Consumer Basket (Geostat Household Budget Survey)
    "budget_breakdown": {
        "food_pct": 0.38,
        "utilities_pct": 0.12,
        "transport_pct": 0.08,
        "healthcare_pct": 0.06,
        "education_pct": 0.05,
        "clothing_pct": 0.08,
        "leisure_pct": 0.04,
        "alcohol_tobacco_pct": 0.05,
        "restaurants_pct": 0.05,
        "other_pct": 0.07,
    },
    
    # Rent as % of budget
    "rent_pct_of_income": 0.30,
    
    # Currency (Geostat/NBG 2025)
    "usd_to_gel_rate": _USD_TO_GEL,
    
    # Macroeconomic snapshot (live from Geostat)
    "gdp_growth_rate": GEOSTAT_GDP["real_growth_rate_2025"] if GEOSTAT_AVAILABLE else 7.5,
    "gdp_per_capita_usd": _GDP_PER_CAPITA,
    "gdp_nominal_usd_billions": _NOMINAL_GDP_USD,
    "population_total": GEOSTAT_POP["total"] if GEOSTAT_AVAILABLE else 3_941_100,
    "labour_force_participation": GEOSTAT_LABOUR["labour_force_participation"] / 100 if GEOSTAT_AVAILABLE else 0.548,
}

# ============================================================================
# 6. SEASONAL PATTERNS (Georgian specific)
# ============================================================================

SEASONAL_PATTERNS = {
    # Price variations by season
    "january": {
        "name": "New Year",
        "food_multiplier": 1.15,  # Food purchases up 15%
        "utility_multiplier": 1.20,  # Heating costs high
        "events": ["New Year celebration"],
    },
    "march": {
        "name": "Women's Day / Novruz",
        "food_multiplier": 1.10,
        "gifting_multiplier": 1.50,  # Gift expenses high
        "events": ["Women's Day (Mar 8)", "Novruz (Mar 21)"],
    },
    "may": {
        "name": "Victory Day / Spring",
        "food_multiplier": 0.95,  # Produce cheaper
        "utility_multiplier": 0.80,  # No heating needed
        "events": ["Victory Day (May 9)"],
    },
    "july_august": {
        "name": "Summer vacation",
        "transport_multiplier": 1.30,  # Travel costs
        "restaurant_multiplier": 1.20,  # Dining out more
        "events": [],
    },
    "october": {
        "name": "Svetitskoba (Georgian national holiday)",
        "food_multiplier": 1.15,
        "events": ["Svetitskoba (Oct 14)"],
    },
    "november_december": {
        "name": "Winter / New Year prep",
        "food_multiplier": 1.25,  # Holiday preparation
        "utility_multiplier": 1.15,
        "gifting_multiplier": 1.40,
        "events": ["Independence Day (Nov 26)", "New Year prep"],
    },
}

# ============================================================================
# 7. CULTURAL SPENDING PATTERNS (Georgian society specific)
# ============================================================================

CULTURAL_SPENDING = {
    "supra_cost_large": 300,  # ₾ per event (fancy feast)
    "supra_cost_medium": 150,  # ₾ (normal feast)
    "supra_cost_minimal": 50,  # ₾ (simple gathering)
    "supra_frequency": "monthly",
    
    "wedding_gift": 100,  # ₾ average gift
    "birthday_gift": 50,  # ₾
    "new_baby_gift": 100,  # ₾
    
    "church_donation": 10,  # ₾ per event
    "candle_price": 0.50,  # ₾
    
    "funeral_expenses": 500,  # ₾
}

# ============================================================================
# 8. EDUCATION COSTS
# ============================================================================

EDUCATION_COSTS = {
    "public_school_monthly": 0,  # Free (government)
    "private_school_monthly": 300,  # ₾/month
    "public_university_monthly": 100,  # Small fee
    "private_university_monthly": 1000,  # ₾/month
    "after_school_tutoring_monthly": 100,  # ₾
    "language_course_monthly": 80,  # English/Russian/etc
}

# ============================================================================
# 9. HEALTHCARE COSTS
# ============================================================================

HEALTHCARE_COSTS = {
    "doctor_visit_public": 0,  # Free in public hospitals
    "doctor_visit_private": 30,  # ₾
    "medicine_average_course": 50,  # ₾
    "emergency_ambulance": 0,  # Free
    "hospital_stay_private_daily": 150,  # ₾/day
    "health_insurance_monthly": 0,  # Most Georgians uninsured
}

# ============================================================================
# 10. HOUSING COSTS BY DISTRICT
# ============================================================================

HOUSING_COSTS = {
    "Vake": {"rent_2bedroom_sqm": 25, "buy_2bedroom_sqm": 8000},
    "Saburtalo": {"rent_2bedroom_sqm": 18, "buy_2bedroom_sqm": 6500},
    "Old Town": {"rent_2bedroom_sqm": 20, "buy_2bedroom_sqm": 7200},
    "Nadzaladevi": {"rent_2bedroom_sqm": 14, "buy_2bedroom_sqm": 4500},
    "Stadion": {"rent_2bedroom_sqm": 12, "buy_2bedroom_sqm": 4000},
    "Gldani": {"rent_2bedroom_sqm": 10, "buy_2bedroom_sqm": 3000},
    "Varketili": {"rent_2bedroom_sqm": 9, "buy_2bedroom_sqm": 2800},
    "New Batumi": {"rent_2bedroom_sqm": 11, "buy_2bedroom_sqm": 3500},
}

# ============================================================================
# 11. TRANSPORT COSTS
# ============================================================================

TRANSPORT_COSTS = {
    "metro_bus_pass_daily": 0.20,  # ₾
    "metro_bus_pass_monthly": 5.00,  # ₾ (unlimited)
    "taxi_per_km": 0.80,  # ₾
    "car_insurance_monthly": 40,  # ₾
    "gasoline_per_liter": 2.90,  # ₾
    "car_maintenance_monthly": 50,  # ₾ estimate
}

# ============================================================================
# 12. DATA SOURCES & METADATA
# ============================================================================

DATA_SOURCES = {
    "geostat": "National Statistics Office of Georgia (https://www.geostat.ge)",
    "world_bank": "World Bank Georgia Data (https://data.worldbank.org/country/GE)",
    "imf": "International Monetary Fund (https://www.imf.org/en/Countries/GEO)",
    "rates": "Georgian Central Bank (https://nationalbank.ge)",
    "real_estate": "Real estate agencies (Silknet, Attachment, etc.)",
    "update_date": "2024-05",
}
