"""
Real Tbilisi district coordinates and landmarks for mapping
"""

# District centers (real latitude/longitude for Tbilisi)
TBILISI_DISTRICTS = {
    "Saburtalo": {
        "lat": 41.7151,
        "lng": 44.7911,
        "name": "Saburtalo",
        "description": "Upper-middle class residential",
        "unemployment_rate": 0.05,
        "avg_salary": 2200
    },
    "Vake": {
        "lat": 41.7179,
        "lng": 44.7722,
        "name": "Vake",
        "description": "Affluent residential & business",
        "unemployment_rate": 0.03,
        "avg_salary": 2800
    },
    "Gldani": {
        "lat": 41.7453,
        "lng": 44.8381,
        "name": "Gldani",
        "description": "Working-class residential",
        "unemployment_rate": 0.12,
        "avg_salary": 1600
    },
    "Varketili": {
        "lat": 41.7574,
        "lng": 44.7686,
        "name": "Varketili",
        "description": "Lower-income residential",
        "unemployment_rate": 0.15,
        "avg_salary": 1400
    },
    "Old Town": {
        "lat": 41.7165,
        "lng": 44.7996,
        "name": "Old Town",
        "description": "Historic center, tourism",
        "unemployment_rate": 0.08,
        "avg_salary": 1800
    },
    "Nadzaladevi": {
        "lat": 41.7248,
        "lng": 44.8056,
        "name": "Nadzaladevi",
        "description": "Mixed residential/industrial",
        "unemployment_rate": 0.09,
        "avg_salary": 1700
    },
    "New Batumi": {
        "lat": 41.7378,
        "lng": 44.7821,
        "name": "New Batumi",
        "description": "Upper-middle residential",
        "unemployment_rate": 0.06,
        "avg_salary": 2300
    },
    "Stadion": {
        "lat": 41.7392,
        "lng": 44.8145,
        "name": "Stadion",
        "description": "Sports & recreation area",
        "unemployment_rate": 0.10,
        "avg_salary": 1900
    },
    "Sanzona": {
        "lat": 41.7420,
        "lng": 44.8020,
        "name": "Sanzona",
        "description": "Residential area",
        "unemployment_rate": 0.11,
        "avg_salary": 1650
    }
}

# Key landmarks in Tbilisi
LANDMARKS = {
    "market_didvbe": {
        "lat": 41.7284,
        "lng": 44.7989,
        "name": "Didvbe Market",
        "type": "market",
        "description": "Main food market"
    },
    "market_grbali": {
        "lat": 41.7180,
        "lng": 44.7650,
        "name": "Grbali Market",
        "type": "market",
        "description": "Fresh produce market"
    },
    "supermarket_carrefour": {
        "lat": 41.7185,
        "lng": 44.7900,
        "name": "Carrefour",
        "type": "supermarket",
        "description": "Modern supermarket"
    },
    "supermarket_goodwill": {
        "lat": 41.7400,
        "lng": 44.7750,
        "name": "GoodWill",
        "type": "supermarket",
        "description": "Modern supermarket"
    },
    "grocery_vake_1": {
        "lat": 41.7145,
        "lng": 44.7825,
        "name": "Vake Supermarket",
        "type": "supermarket",
        "description": "Local grocery store"
    },
    "grocery_vake_2": {
        "lat": 41.7195,
        "lng": 44.7755,
        "name": "Vake Fresh",
        "type": "supermarket",
        "description": "Grocery & produce"
    },
    "grocery_saburtalo_1": {
        "lat": 41.7165,
        "lng": 44.7925,
        "name": "Saburtalo Market",
        "type": "supermarket",
        "description": "Community grocery"
    },
    "grocery_saburtalo_2": {
        "lat": 41.7135,
        "lng": 44.7885,
        "name": "Saburtalo Shop",
        "type": "supermarket",
        "description": "Neighborhood store"
    },
    "grocery_oldtown_1": {
        "lat": 41.7180,
        "lng": 44.8010,
        "name": "Old Town Market",
        "type": "market",
        "description": "Historic bazaar"
    },
    "grocery_nadzaladevi_1": {
        "lat": 41.7260,
        "lng": 44.8095,
        "name": "Nadzaladevi Grocery",
        "type": "supermarket",
        "description": "Local store"
    },
    "grocery_gldani_1": {
        "lat": 41.7480,
        "lng": 44.8405,
        "name": "Gldani Fresh",
        "type": "supermarket",
        "description": "Community market"
    },
    "grocery_gldani_2": {
        "lat": 41.7425,
        "lng": 44.8360,
        "name": "Gldani Supermarket",
        "type": "supermarket",
        "description": "Neighborhood grocery"
    },
    "grocery_varketili_1": {
        "lat": 41.7595,
        "lng": 44.7705,
        "name": "Varketili Market",
        "type": "supermarket",
        "description": "Local grocery store"
    },
    "grocery_varketili_2": {
        "lat": 41.7550,
        "lng": 44.7665,
        "name": "Varketili Shop",
        "type": "supermarket",
        "description": "Community store"
    },
    "grocery_newbatumi_1": {
        "lat": 41.7398,
        "lng": 44.7835,
        "name": "New Batumi Grocery",
        "type": "supermarket",
        "description": "Local supermarket"
    },
    "grocery_stadion_1": {
        "lat": 41.7410,
        "lng": 44.8165,
        "name": "Stadion Market",
        "type": "supermarket",
        "description": "Area grocery"
    },
    "merchant_city": {
        "lat": 41.7250,
        "lng": 44.8050,
        "name": "Merchant City",
        "type": "shopping",
        "description": "Central shopping district"
    },
    "metro_station_1": {
        "lat": 41.7400,
        "lng": 44.7900,
        "name": "Metro Station",
        "type": "transport",
        "description": "Main transportation hub"
    }
}

# Activity locations by district (work, school, leisure)
ACTIVITY_LOCATIONS = {
    "work_centers": {
        "Vake": {"lat": 41.7179, "lng": 44.7722, "density": 0.8},
        "Old Town": {"lat": 41.7165, "lng": 44.7996, "density": 0.6},
        "Saburtalo": {"lat": 41.7151, "lng": 44.7911, "density": 0.5},
    },
    "schools": [
        {"lat": 41.7200, "lng": 44.7850, "name": "School #1"},
        {"lat": 41.7300, "lng": 44.7900, "name": "School #2"},
        {"lat": 41.7450, "lng": 44.8350, "name": "School #3"},
        {"lat": 41.7500, "lng": 44.7700, "name": "School #4"},
    ],
    "hospitals": [
        {"lat": 41.7165, "lng": 44.7996, "name": "Central Hospital"},
        {"lat": 41.7450, "lng": 44.8350, "name": "Regional Hospital"},
    ],
    "parks": [
        {"lat": 41.7100, "lng": 44.7850, "name": "Metekhi Park"},
        {"lat": 41.7350, "lng": 44.8000, "name": "Narikala Park"},
    ]
}

# Map bounds for Tbilisi
MAP_CENTER = {"lat": 41.7251, "lng": 44.7879}
MAP_BOUNDS = {
    "north": 41.7700,
    "south": 41.7000,
    "east": 44.8600,
    "west": 44.7400
}

def get_district_by_name(district_name):
    """Get district info by name"""
    return TBILISI_DISTRICTS.get(district_name)

def get_all_districts():
    """Get all districts"""
    return TBILISI_DISTRICTS

def get_landmark_location(landmark_type):
    """Get random landmark of a type"""
    import random
    matching = {k: v for k, v in LANDMARKS.items() if v["type"] == landmark_type}
    if matching:
        return list(matching.values())[random.randint(0, len(matching) - 1)]
    return None

def add_noise_to_coordinates(lat, lng, noise_radius_km=1):
    """Add random noise to coordinates (for variation within district)"""
    import random
    # Approximate: 1 degree = ~111 km
    noise_degrees = noise_radius_km / 111.0
    new_lat = lat + random.uniform(-noise_degrees, noise_degrees)
    new_lng = lng + random.uniform(-noise_degrees, noise_degrees)
    return new_lat, new_lng
