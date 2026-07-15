"""
Track agent locations and movements in real-time
"""

import json
from typing import Dict, List, Tuple
from datetime import datetime
from data.tbilisi_coordinates import add_noise_to_coordinates, TBILISI_DISTRICTS, LANDMARKS

class LocationTracker:
    """Tracks agent positions, movements, and activities"""
    
    def __init__(self):
        self.agent_locations: Dict[str, Dict] = {}
        self.movement_history: List[Dict] = []
        self.activity_log: List[Dict] = []
        self.current_step = 0
        
    def add_agent(self, agent_id: str, agent_name: str, district: str):
        """Register agent with initial location"""
        district_info = TBILISI_DISTRICTS.get(district, TBILISI_DISTRICTS["Saburtalo"])
        lat, lng = add_noise_to_coordinates(
            district_info["lat"], 
            district_info["lng"], 
            noise_radius_km=1.5
        )
        
        self.agent_locations[agent_id] = {
            "name": agent_name,
            "district": district,
            "lat": lat,
            "lng": lng,
            "activity": "home",
            "stress": 50,
            "budget": 500,
            "role": "person",
            "last_update": 0
        }
    
    def update_agent_location(self, agent_id: str, activity: str, destination_type: str = None):
        """Update agent location based on activity"""
        if agent_id not in self.agent_locations:
            return
        
        agent = self.agent_locations[agent_id]
        old_lat, old_lng = agent["lat"], agent["lng"]
        
        # Determine new location based on activity
        if activity == "home":
            district_info = TBILISI_DISTRICTS.get(agent["district"], TBILISI_DISTRICTS["Saburtalo"])
            new_lat, new_lng = add_noise_to_coordinates(district_info["lat"], district_info["lng"], 1.0)
        
        elif activity == "work":
            # Work locations are typically in central areas
            work_districts = ["Vake", "Old Town", "Saburtalo"]
            import random
            work_dist = random.choice(work_districts)
            district_info = TBILISI_DISTRICTS[work_dist]
            new_lat, new_lng = add_noise_to_coordinates(district_info["lat"], district_info["lng"], 0.8)
        
        elif activity == "shopping":
            # Shopping at markets or supermarkets
            landmark = LANDMARKS.get(destination_type or "market_didvbe")
            new_lat = landmark["lat"] if landmark else old_lat
            new_lng = landmark["lng"] if landmark else old_lng
            new_lat, new_lng = add_noise_to_coordinates(new_lat, new_lng, 0.2)
        
        elif activity == "school":
            # Schools are fixed locations
            import random
            school = random.choice([
                {"lat": 41.7200, "lng": 44.7850},
                {"lat": 41.7300, "lng": 44.7900},
                {"lat": 41.7450, "lng": 44.8350},
                {"lat": 41.7500, "lng": 44.7700},
            ])
            new_lat, new_lng = add_noise_to_coordinates(school["lat"], school["lng"], 0.3)
        
        elif activity == "leisure":
            # Parks and leisure areas
            import random
            park = random.choice([
                {"lat": 41.7100, "lng": 44.7850},
                {"lat": 41.7350, "lng": 44.8000},
            ])
            new_lat, new_lng = add_noise_to_coordinates(park["lat"], park["lng"], 0.4)
        
        else:
            # Default: stay at current location with slight movement
            new_lat, new_lng = add_noise_to_coordinates(old_lat, old_lng, 0.1)
        
        # Record movement
        self.movement_history.append({
            "timestamp": self.current_step,
            "agent": agent_id,
            "from": {"lat": old_lat, "lng": old_lng, "activity": agent["activity"]},
            "to": {"lat": new_lat, "lng": new_lng, "activity": activity}
        })
        
        # Update agent
        agent["lat"] = new_lat
        agent["lng"] = new_lng
        agent["activity"] = activity
        agent["last_update"] = self.current_step
    
    def update_agent_state(self, agent_id: str, stress: float, budget: float):
        """Update agent's well-being metrics"""
        if agent_id not in self.agent_locations:
            return
        
        self.agent_locations[agent_id]["stress"] = min(100, max(0, stress))
        self.agent_locations[agent_id]["budget"] = max(0, budget)
    
    def log_activity(self, agent_name: str, activity_text: str):
        """Log an activity event"""
        self.activity_log.append({
            "timestamp": self.current_step,
            "agent": agent_name,
            "activity": activity_text
        })
    
    def step(self):
        """Advance the step counter"""
        self.current_step += 1
    
    def get_agent_locations(self) -> Dict:
        """Get all agent locations"""
        return self.agent_locations
    
    def get_map_data(self) -> Dict:
        """Get formatted data for map visualization"""
        agents = []
        for agent_id, agent_data in self.agent_locations.items():
            agents.append({
                "id": agent_id,
                "name": agent_data["name"],
                "lat": agent_data["lat"],
                "lng": agent_data["lng"],
                "activity": agent_data["activity"],
                "stress": agent_data["stress"],
                "budget": agent_data["budget"],
                "role": agent_data["role"],
                "district": agent_data["district"]
            })
        
        return {
            "agents": agents,
            "step": self.current_step,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_recent_activities(self, limit=20) -> List[Dict]:
        """Get recent activity log"""
        return self.activity_log[-limit:]
    
    def get_movement_summary(self) -> Dict:
        """Get summary of agent movements"""
        by_activity = {}
        for agent_id, agent in self.agent_locations.items():
            activity = agent["activity"]
            if activity not in by_activity:
                by_activity[activity] = []
            by_activity[activity].append(agent_id)
        
        return {
            activity: len(agents) for activity, agents in by_activity.items()
        }
    
    def save_state(self, filepath: str):
        """Save tracker state to JSON"""
        data = {
            "current_step": self.current_step,
            "agent_locations": self.agent_locations,
            "movement_history": self.movement_history[-1000:],  # Last 1000 movements
            "activity_log": self.activity_log[-500:],  # Last 500 activities
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_state(self, filepath: str):
        """Load tracker state from JSON"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.current_step = data.get("current_step", 0)
            self.agent_locations = data.get("agent_locations", {})
            self.movement_history = data.get("movement_history", [])
            self.activity_log = data.get("activity_log", [])
        except Exception as e:
            print(f"Error loading location tracker state: {e}")
