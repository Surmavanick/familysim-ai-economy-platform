
import random
from world.tbilisi_geography import get_district_for_agent, get_economic_modifiers_for_district

def generate_random_family(family_id):
    sur_names = ["Kapanadze", "Gelasvili", "Maisuradze", "Giorgadze", "Lomidze", "Tsiklauri", "Bolkvadze"]
    first_names_m = ["Luka", "Giorgi", "Davit", "Nika", "Zura", "Otar"]
    first_names_f = ["Nino", "Mariam", "Ana", "Lela", "Salome", "Eka"]
    
    surname = random.choice(sur_names)
    num_children = random.randint(1, 3)
    
    # Assign to Tbilisi district
    district = get_district_for_agent(family_id)
    modifiers = get_economic_modifiers_for_district(district)
    income_modifier = modifiers.get("income_modifier", 1.0)
    
    family_config = []
    
    # Father
    family_config.append({
        "name": f"{random.choice(first_names_m)} {surname}",
        "role": "father",
        "age": random.randint(30, 55),
        "district": district,
        "personality": {
            "frugality": random.uniform(0.3, 0.9),
            "patience": random.uniform(0.4, 0.8),
            "brand_loyalty": random.uniform(0.2, 0.7),
            "impulsivity": random.uniform(0.1, 0.6)
        }
    })
    
    # Mother
    family_config.append({
        "name": f"{random.choice(first_names_f)} {surname}",
        "role": "mother",
        "age": random.randint(28, 52),
        "district": district,
        "personality": {
            "frugality": random.uniform(0.3, 0.9),
            "patience": random.uniform(0.5, 0.9),
            "brand_loyalty": random.uniform(0.3, 0.8),
            "impulsivity": random.uniform(0.2, 0.7)
        }
    })
    
    # Kids
    for i in range(num_children):
        family_config.append({
            "name": f"Kid {i+1} {surname}",
            "role": "child",
            "age": random.randint(5, 18),
            "district": district,
            "personality": {
                "frugality": random.uniform(0.1, 0.4),
                "patience": random.uniform(0.2, 0.6),
                "brand_loyalty": random.uniform(0.1, 0.5),
                "impulsivity": random.uniform(0.4, 0.9)
            }
        })
    
    # Adjust initial budget based on district
    base_budget = random.uniform(1500, 5000)
    adjusted_budget = base_budget * income_modifier
    
    return {
        "household_id": family_id,
        "surname": surname,
        "district": district,
        "members": family_config,
        "initial_budget": adjusted_budget
    }

def generate_population(n=10):
    return [generate_random_family(i) for i in range(n)]
