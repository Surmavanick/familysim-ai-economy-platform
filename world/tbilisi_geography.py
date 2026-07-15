"""
Tbilisi geography, neighborhoods, and economic data.
Real-world accurate locations and economic information.
"""

# Tbilisi city districts with coordinates (center lat/lon) and characteristics
TBILISI_DISTRICTS = {
    "Vake": {
        "lat": 41.7151,
        "lon": 44.7735,
        "economic_grade": "high",  # Wealthy area
        "population_density": "medium",
        "avg_income": 3200,  # GEL per month
        "unemployment_rate": 0.02,
        "crime_rate": 0.01,
    },
    "Saburtalo": {
        "lat": 41.7049,
        "lon": 44.8086,
        "economic_grade": "high",
        "population_density": "high",
        "avg_income": 2800,
        "unemployment_rate": 0.03,
        "crime_rate": 0.02,
    },
    "Old Town": {
        "lat": 41.7151,
        "lon": 44.7945,
        "economic_grade": "mixed",
        "population_density": "very_high",
        "avg_income": 1800,
        "unemployment_rate": 0.08,
        "crime_rate": 0.05,
    },
    "Gldani": {
        "lat": 41.7385,
        "lon": 44.8580,
        "economic_grade": "low",  # Soviet-era settlement
        "population_density": "high",
        "avg_income": 1200,
        "unemployment_rate": 0.15,
        "crime_rate": 0.08,
    },
    "Varketili": {
        "lat": 41.6972,
        "lon": 44.8445,
        "economic_grade": "low",
        "population_density": "high",
        "avg_income": 1100,
        "unemployment_rate": 0.18,
        "crime_rate": 0.10,
    },
    "Nadzaladevi": {
        "lat": 41.7636,
        "lon": 44.8269,
        "economic_grade": "medium",
        "population_density": "medium",
        "avg_income": 1500,
        "unemployment_rate": 0.12,
        "crime_rate": 0.06,
    },
    "New Batumi": {
        "lat": 41.7502,
        "lon": 44.7480,
        "economic_grade": "medium",
        "population_density": "medium",
        "avg_income": 1900,
        "unemployment_rate": 0.06,
        "crime_rate": 0.03,
    },
    "Stadion": {
        "lat": 41.6550,
        "lon": 44.7750,
        "economic_grade": "medium",
        "population_density": "medium",
        "avg_income": 1700,
        "unemployment_rate": 0.10,
        "crime_rate": 0.04,
    },
}

# Real Tbilisi supermarkets/stores with locations
TBILISI_STORES = [
    {"name": "Carrefour Vake", "district": "Vake", "lat": 41.7151, "lon": 44.7735, "price_level": 1.0},
    {"name": "Carrefour Saburtalo", "district": "Saburtalo", "lat": 41.7049, "lon": 44.8086, "price_level": 1.0},
    {"name": "Goodwill Old Town", "district": "Old Town", "lat": 41.7151, "lon": 44.7945, "price_level": 0.85},
    {"name": "Magniti Gldani", "district": "Gldani", "lat": 41.7385, "lon": 44.8580, "price_level": 0.90},
    {"name": "Magniti Varketili", "district": "Varketili", "lat": 41.6972, "lon": 44.8445, "price_level": 0.90},
    {"name": "Spar Nadzaladevi", "district": "Nadzaladevi", "lat": 41.7636, "lon": 44.8269, "price_level": 0.95},
]

# Georgian economic events specific to Tbilisi
GEORGIAN_ECONOMIC_EVENTS = [
    {
        "name": "Government Child Benefit",
        "type": "income",
        "monthly_payment": 80,  # GEL
        "trigger_months": [1, 4, 7, 10],  # Quarterly
        "target_roles": ["mother", "father"],
        "description": "Georgian state child support benefit"
    },
    {
        "name": "Pension Payment",
        "type": "income",
        "monthly_payment": 200,  # Estimated Georgian pension
        "trigger_months": list(range(1, 13)),
        "target_roles": ["grandparent"],
        "description": "Old-age pension payment"
    },
    {
        "name": "Utility Price Spike",
        "type": "expense",
        "cost": 150,  # GEL per month in winter
        "trigger_months": [11, 12, 1, 2, 3],  # Winter
        "probability": 0.7,
        "description": "Heating costs increase in winter"
    },
    {
        "name": "School Year Starts",
        "type": "expense",
        "cost": 500,  # GEL per child
        "trigger_months": [9],
        "target_roles": ["child"],
        "probability": 1.0,
        "description": "School uniforms, books, supplies"
    },
    {
        "name": "Tbilisi Job Market Surge",
        "type": "opportunity",
        "salary_bonus": 0.15,  # 15% salary boost
        "trigger_months": [3, 9],  # Spring, autumn
        "probability": 0.4,
        "description": "Tourism and IT boom seasons"
    },
    {
        "name": "Currency Fluctuation (GEL Devaluation)",
        "type": "inflation",
        "rate": 1.03,  # 3% price increase
        "trigger_months": [2, 8],  # Seasonal
        "probability": 0.3,
        "description": "GEL weakens against USD/EUR"
    },
    {
        "name": "Healthcare Emergency",
        "type": "expense",
        "cost": 300,  # GEL
        "probability": 0.05,  # 5% chance per month
        "description": "Medical emergency or doctor visit"
    },
    {
        "name": "New Year Celebration",
        "type": "cultural",
        "spending_multiplier": 2.0,
        "trigger_months": [12, 1],
        "description": "Increased holiday spending"
    },
]

# Georgian cultural events
GEORGIAN_HOLIDAYS = {
    1: "New Year",
    1: "Orthodox Christmas",
    3: "International Women's Day",
    5: "Victory Day",
    8: "Assumption of Mary",
    10: "Svetitskoba (St. Nino's Day)",
    11: "Independence Day",
    12: "Independence Day Holiday",
}

# Real Georgian market products
GEORGIAN_PRODUCTS = {
    "khachapuri": {"price": 3.50, "category": "Bread", "popularity": 0.95},
    "bread": {"price": 1.20, "category": "Bread", "popularity": 0.98},
    "milk": {"price": 4.50, "category": "Dairy", "popularity": 0.90},
    "cheese": {"price": 8.00, "category": "Dairy", "popularity": 0.85},
    "chicken": {"price": 12.00, "category": "Meat", "popularity": 0.88},
    "beef": {"price": 18.00, "category": "Meat", "popularity": 0.80},
    "eggs": {"price": 6.00, "category": "Dairy", "popularity": 0.92},
    "tomatoes": {"price": 2.50, "category": "Produce", "popularity": 0.85},
    "potatoes": {"price": 1.50, "category": "Produce", "popularity": 0.90},
    "wine": {"price": 15.00, "category": "Drinks", "popularity": 0.75},  # Georgian wine
    "chacha": {"price": 8.00, "category": "Drinks", "popularity": 0.60},  # Georgian brandy
}


def get_district_for_agent(agent_id: int) -> str:
    """Randomly assign agent to a Tbilisi district based on economic distribution."""
    import random
    # Weighted distribution - more agents in affordable areas
    districts = list(TBILISI_DISTRICTS.keys())
    weights = [0.15, 0.15, 0.10, 0.20, 0.20, 0.10, 0.05, 0.05]  # More in Gldani/Varketili
    return random.choices(districts, weights=weights, k=1)[0]


def get_economic_modifiers_for_district(district: str) -> dict:
    """Get economic modifiers based on district."""
    if district not in TBILISI_DISTRICTS:
        return {}
    
    d = TBILISI_DISTRICTS[district]
    grade = d["economic_grade"]
    # Map all grades to modifier values
    grade_map = {"high": 1.15, "mixed": 1.0, "medium": 1.0, "low": 0.75}
    price_map = {"high": 1.1, "mixed": 1.0, "medium": 1.0, "low": 0.9}
    
    return {
        "income_modifier": grade_map.get(grade, 1.0),
        "price_modifier": price_map.get(grade, 1.0),
        "unemployment_risk": d["unemployment_rate"],
        "crime_risk": d["crime_rate"],
    }
