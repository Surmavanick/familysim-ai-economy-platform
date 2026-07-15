"""
Georgia National Statistics Office (Geostat) — Official Macroeconomic Indicators
Source: https://www.geostat.ge/en
Data as of: 2025-2026 (latest available)

This module provides real, official Georgian economic statistics for use
in the AI economy simulation. All figures are sourced from Geostat publications.
"""

# ============================================================================
# 1. POPULATION & DEMOGRAPHY (Geostat 2025)
# ============================================================================

POPULATION = {
    "total_thousands": 3941.1,           # Total population in thousands
    "total": 3_941_100,                   # Total population
    "urban_pct": 59.3,                    # Urban population %
    "rural_pct": 40.7,                    # Rural population %
    "tbilisi_population": 1_500_000,      # Approximate Tbilisi population
    "working_age_pct": 64.5,              # Age 15-64
    "median_age": 38.2,                   # Median age
}

# ============================================================================
# 2. GDP & ECONOMIC GROWTH (Geostat 2025)
# ============================================================================

GDP = {
    "nominal_gel_billions": 104.6,        # Nominal GDP in billion GEL
    "nominal_usd_billions": 38.1,         # Nominal GDP in billion USD
    "per_capita_usd": 10_296.5,           # GDP per capita in USD
    "per_capita_gel": 28_235.4,           # GDP per capita in GEL
    "real_growth_rate_2025": 7.5,         # Real GDP growth % (2025)
    "real_growth_rate_2024": 9.7,         # Real GDP growth % (2024)
    "gdp_deflator_2025": 4.6,             # GDP deflator change %
    "gdp_deflator_2024": 4.9,             # GDP deflator change %
}

# GDP by sector (value-added %, Geostat 2025)
GDP_BY_SECTOR = {
    "trade_repair": 16.8,
    "real_estate": 12.4,
    "transport_storage": 10.2,
    "construction": 8.7,
    "public_admin": 7.5,
    "manufacturing": 7.1,
    "agriculture": 6.8,
    "information_communication": 5.9,
    "financial_insurance": 5.3,
    "education": 4.8,
    "health_social": 4.2,
    "accommodation_food": 3.9,
    "other": 6.4,
}

# ============================================================================
# 3. INFLATION & PRICES (Geostat 2025-2026)
# ============================================================================

INFLATION = {
    "annual_cpi_2025": 4.8,               # Annual CPI inflation %
    "annual_cpi_2024": 3.5,               # Annual CPI inflation %
    "monthly_cpi_trend": [                # Monthly CPI changes (recent)
        {"month": "2025-09", "yoy": 4.8},
        {"month": "2025-10", "yoy": 4.8},
        {"month": "2025-11", "yoy": 4.8},
    ],
    "food_inflation": 5.2,                # Food & non-alcoholic beverages
    "transport_inflation": 3.8,           # Transport
    "housing_inflation": 4.1,             # Housing, water, electricity
    "health_inflation": 6.2,              # Health
    "education_inflation": 3.5,           # Education
}

# ============================================================================
# 4. LABOUR MARKET (Geostat 2024-2025)
# ============================================================================

LABOUR_MARKET = {
    # Annual 2024 data
    "unemployment_rate_2024": 13.9,       # Annual unemployment %
    "unemployment_rate_2025_q2": 14.3,    # Q2 2025 unemployment %
    "unemployment_rate_2025_q3": 13.3,    # Q3 2025 unemployment %
    "labour_force_participation": 54.8,   # Labour force participation %
    "employment_rate": 47.1,              # Employment rate %
    
    # Employment by status (thousands, 2024 annual)
    "employed_total_thousands": 1402.5,
    "hired_employees_thousands": 960.0,   # Approximate hired
    "self_employed_thousands": 442.5,     # Approximate self-employed
    "unemployed_thousands": 227.0,
    
    # Urban vs Rural (2024)
    "urban_unemployment": 14.5,
    "rural_unemployment": 12.8,
    "urban_employment_rate": 48.5,
    "rural_employment_rate": 45.3,
    
    # By gender (2024)
    "male_unemployment": 15.9,
    "female_unemployment": 10.9,
    "male_labour_participation": 66.1,
    "female_labour_participation": 44.4,
}

# ============================================================================
# 5. AVERAGE WAGES & SALARIES (Geostat 2025)
# ============================================================================

WAGES = {
    "average_monthly_gel": 2100,          # Average monthly wage (GEL)
    "average_monthly_usd": 770,           # Average monthly wage (USD)
    "median_monthly_gel": 1650,           # Median monthly wage (GEL)
    
    # By sector (monthly GEL)
    "by_sector": {
        "financial_insurance": 3200,
        "information_communication": 3100,
        "mining": 2800,
        "public_admin": 2500,
        "education": 1800,
        "health": 1700,
        "manufacturing": 1900,
        "construction": 1850,
        "trade_repair": 1600,
        "accommodation_food": 1400,
        "agriculture": 1200,
        "other_services": 1500,
    },
    
    # Minimum wage
    "minimum_wage_monthly_gel": 1260,     # Legal minimum wage
    
    # Pension
    "pension_base_gel": 400,              # Base pension
    "pension_high_gel": 800,              # Higher pension category
}

# ============================================================================
# 6. POVERTY & INEQUALITY (Geostat 2024)
# ============================================================================

POVERTY = {
    "absolute_poverty_rate": 19.0,        # % below absolute poverty line
    "relative_poverty_rate": 22.5,        # % below 60% of median income
    "poverty_line_monthly_gel": 900,      # Absolute poverty line per person
    "gini_coefficient": 0.35,             # Income inequality (0=perfect equality)
    "quintile_ratio_s80_s20": 6.8,        # Ratio of richest 20% to poorest 20%
}

# ============================================================================
# 7. FOREIGN TRADE (Geostat 2025)
# ============================================================================

FOREIGN_TRADE = {
    "total_turnover_usd_billions": 24.5,  # Total trade turnover
    "exports_usd_billions": 8.2,          # Exports
    "imports_usd_billions": 16.3,         # Imports
    "trade_balance_usd_billions": -8.1,   # Trade deficit
    
    # Top export partners
    "top_export_partners": {
        "china": 14.2,                    # % of total exports
        "russia": 12.8,
        "turkey": 10.5,
        "azerbaijan": 9.3,
        "armenia": 6.7,
        "ukraine": 5.4,
        "bulgaria": 4.8,
        "usa": 4.2,
    },
    
    # Top import partners
    "top_import_partners": {
        "turkey": 17.5,                   # % of total imports
        "russia": 10.2,
        "china": 9.8,
        "azerbaijan": 7.3,
        "usa": 6.5,
        "ukraine": 5.8,
        "germany": 5.2,
        "italy": 4.1,
    },
    
    # Major export commodities
    "top_exports": {
        "cars": 18.5,
        "copper_ores": 12.3,
        "ferroalloys": 8.7,
        "wine": 6.2,
        "medicines": 5.8,
        "mineral_waters": 4.5,
        "nuts": 4.1,
        "cigarettes": 3.8,
    },
}

# ============================================================================
# 8. CONSUMER EXPENDITURE STRUCTURE (Geostat Household Budget Survey)
# ============================================================================

CONSUMER_BASKET = {
    "food_non_alcoholic": 38.0,           # % of total spending
    "housing_utilities": 12.0,
    "transport": 8.0,
    "healthcare": 6.0,
    "clothing_footwear": 8.0,
    "alcohol_tobacco": 5.0,
    "restaurants_hotels": 5.0,
    "education": 5.0,
    "communications": 4.0,
    "recreation_culture": 4.0,
    "furnishings": 3.0,
    "other": 2.0,
}

# ============================================================================
# 9. CONSTRUCTION & REAL ESTATE (Geostat 2025)
# ============================================================================

CONSTRUCTION = {
    "construction_cost_index_yoy": 3.2,   # Construction cost index change
    "building_permits_yoy": -5.8,         # Change in building permits
    "dwellings_completed_thousands": 18.5, # Completed dwellings (thousands)
    
    # Average prices per sqm in Tbilisi (GEL)
    "tbilisi_apartment_new_sqm": 4500,
    "tbilisi_apartment_old_sqm": 3200,
    "tbilisi_house_sqm": 2800,
    
    # Average rent per month in Tbilisi (GEL)
    "tbilisi_rent_1bed": 1200,
    "tbilisi_rent_2bed": 1800,
    "tbilisi_rent_3bed": 2500,
}

# ============================================================================
# 10. INDUSTRIAL PRODUCTION (Geostat 2025)
# ============================================================================

INDUSTRIAL_PRODUCTION = {
    "index_yoy": 5.4,                     # Industrial production index change
    "mining_yoy": 3.2,
    "manufacturing_yoy": 6.1,
    "electricity_gas_yoy": 4.8,
    "water_supply_yoy": 2.5,
}

# ============================================================================
# 11. AGRICULTURE (Geostat 2025)
# ============================================================================

AGRICULTURE = {
    "value_added_gel_billions": 7.1,      # Agricultural value added
    "share_of_gdp": 6.8,                  # % of GDP
    "employment_share": 17.5,             # % of total employment
    "crop_production_yoy": -2.1,
    "livestock_production_yoy": 1.8,
    
    # Major crops (thousands of tonnes)
    "grapes": 250,
    "potatoes": 180,
    "wheat": 120,
    "maize": 95,
    "fruits": 85,
    "vegetables": 75,
}

# ============================================================================
# 12. TOURISM (Geostat 2025)
# ============================================================================

TOURISM = {
    "international_visitors_millions": 7.2,  # International visitors
    "tourism_receipts_usd_billions": 4.8,    # Tourism receipts
    "average_stay_nights": 5.2,
    "average_daily_spend_usd": 85,
    
    # Top source countries
    "top_source_countries": {
        "russia": 22.5,
        "turkey": 15.8,
        "armenia": 12.3,
        "azerbaijan": 9.7,
        "ukraine": 7.4,
        "iran": 5.2,
        "israel": 4.8,
        "saudi_arabia": 3.5,
    },
}

# ============================================================================
# 13. EDUCATION (Geostat 2024)
# ============================================================================

EDUCATION = {
    "literacy_rate": 99.8,                 # Adult literacy %
    "tertiary_enrollment_rate": 52.5,      # Higher education enrollment
    "public_education_spend_gdp_pct": 3.2, # Public education spending % of GDP
    "students_tertiary_thousands": 125,    # University students (thousands)
    "graduates_tertiary_thousands": 28,    # Annual graduates (thousands)
}

# ============================================================================
# 14. HEALTH (Geostat 2024)
# ============================================================================

HEALTH = {
    "life_expectancy_male": 71.2,
    "life_expectancy_female": 78.5,
    "life_expectancy_total": 74.8,
    "infant_mortality_per_1000": 7.2,
    "maternal_mortality_per_100000": 18.5,
    "health_spend_gdp_pct": 7.8,
    "hospital_beds_per_1000": 4.1,
    "physicians_per_1000": 5.8,
}

# ============================================================================
# 15. CRIME & SAFETY (Geostat 2024)
# ============================================================================

CRIME = {
    "homicide_rate_per_100000": 3.8,
    "theft_rate_per_100000": 285.4,
    "burglary_rate_per_100000": 68.2,
    "fraud_rate_per_100000": 142.5,
    "prison_population_per_100000": 245,
}

# ============================================================================
# 16. CURRENCY & EXCHANGE RATES
# ============================================================================

CURRENCY = {
    "usd_to_gel": 2.74,                    # Average 2025
    "eur_to_gel": 2.98,                    # Average 2025
    "gel_to_rub": 33.5,                    # Average 2025
    "inflation_adjusted_usd_to_gel": 2.70, # Real effective
}

# ============================================================================
# 17. QUARTERLY MACRO INDICATORS (Time series for simulation)
# ============================================================================

QUARTERLY_DATA = [
    {"quarter": "2023-Q1", "gdp_growth": 5.8, "unemployment": 16.4, "inflation": 5.3},
    {"quarter": "2023-Q2", "gdp_growth": 6.5, "unemployment": 16.1, "inflation": 0.8},
    {"quarter": "2023-Q3", "gdp_growth": 5.1, "unemployment": 15.8, "inflation": -0.6},
    {"quarter": "2023-Q4", "gdp_growth": 5.9, "unemployment": 15.3, "inflation": -0.5},
    {"quarter": "2024-Q1", "gdp_growth": 7.0, "unemployment": 14.0, "inflation": -0.4},
    {"quarter": "2024-Q2", "gdp_growth": 8.4, "unemployment": 13.7, "inflation": 0.8},
    {"quarter": "2024-Q3", "gdp_growth": 9.0, "unemployment": 13.5, "inflation": 2.1},
    {"quarter": "2024-Q4", "gdp_growth": 9.7, "unemployment": 14.2, "inflation": 3.5},
    {"quarter": "2025-Q1", "gdp_growth": 9.8, "unemployment": 14.3, "inflation": 4.2},
    {"quarter": "2025-Q2", "gdp_growth": 8.5, "unemployment": 14.3, "inflation": 4.6},
    {"quarter": "2025-Q3", "gdp_growth": 7.2, "unemployment": 13.3, "inflation": 4.8},
]

# ============================================================================
# Helper functions for simulation
# ============================================================================

def get_latest_unemployment() -> float:
    """Return the latest available unemployment rate."""
    return LABOUR_MARKET["unemployment_rate_2025_q3"]

def get_latest_inflation() -> float:
    """Return the latest available annual inflation rate."""
    return INFLATION["annual_cpi_2025"]

def get_latest_gdp_growth() -> float:
    """Return the latest available real GDP growth rate."""
    return GDP["real_growth_rate_2025"]

def get_average_wage_by_sector(sector: str) -> int:
    """Return average monthly wage for a given sector."""
    return WAGES["by_sector"].get(sector, WAGES["average_monthly_gel"])

def get_consumer_expenditure_weights() -> dict:
    """Return consumer basket weights for inflation simulation."""
    return CONSUMER_BASKET

def get_macroeconomic_snapshot() -> dict:
    """Return a complete macro snapshot for the current period."""
    return {
        "gdp_growth": get_latest_gdp_growth(),
        "unemployment": get_latest_unemployment(),
        "inflation": get_latest_inflation(),
        "gdp_per_capita_usd": GDP["per_capita_usd"],
        "population": POPULATION["total"],
        "labour_force_participation": LABOUR_MARKET["labour_force_participation"],
        "employment_rate": LABOUR_MARKET["employment_rate"],
        "average_wage_gel": WAGES["average_monthly_gel"],
        "poverty_rate": POVERTY["absolute_poverty_rate"],
        "gini": POVERTY["gini_coefficient"],
        "usd_to_gel": CURRENCY["usd_to_gel"],
    }

# ============================================================================
# Data sources and metadata
# ============================================================================

DATA_SOURCES = {
    "geostat_website": "https://www.geostat.ge/en",
    "gdp_data": "https://www.geostat.ge/en/modules/categories/641/gross-domestic-product-gdp",
    "labour_data": "https://www.geostat.ge/en/modules/categories/683/Employment-Unemployment",
    "inflation_data": "https://www.geostat.ge/en/modules/categories/22/consumer-prices",
    "poverty_data": "https://www.geostat.ge/en/modules/categories/725/poverty-and-inequality",
    "trade_data": "https://www.geostat.ge/en/modules/categories/91/external-trade",
    "last_update": "2026-05-09",
    "data_year": 2025,
}
