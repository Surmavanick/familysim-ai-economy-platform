import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "data" / "tbilisi_coordinates.py"

with open(TARGET, "r") as f:
    content = f.read()

sanzona = """    "Stadion": {
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
    }"""
content = content.replace('''    "Stadion": {
        "lat": 41.7392,
        "lng": 44.8145,
        "name": "Stadion",
        "description": "Sports & recreation area",
        "unemployment_rate": 0.10,
        "avg_salary": 1900
    }''', sanzona)

with open(TARGET, "w") as f:
    f.write(content)
