"""
Life Simulation Module - transforms agents from "homo economicus" to synthetic humans
Focuses on: routines, emotions, social influence, identity, culture
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

class ActivityType(Enum):
    """Daily activities beyond economics"""
    SLEEP = "sleep"
    WORK = "work"
    SCHOOL = "school"
    FAMILY_TIME = "family_time"
    SOCIALIZING = "socializing"
    LEISURE = "leisure"
    SHOPPING = "shopping"
    EATING = "eating"
    EXERCISE = "exercise"
    SCROLLING = "scrolling_social_media"

class EmotionalState(Enum):
    """Core emotional states (not just stress)"""
    HAPPY = "happy"
    ANXIOUS = "anxious"
    BORED = "bored"
    TIRED = "tired"
    EXCITED = "excited"
    ASHAMED = "ashamed"
    JEALOUS = "jealous"
    CONTENT = "content"

@dataclass
class EmotionalProfile:
    """Emotional state tracking"""
    stress: float = 50.0           # 0-100
    happiness: float = 50.0        # 0-100
    boredom: float = 50.0          # 0-100
    fatigue: float = 30.0          # 0-100
    jealousy: float = 20.0         # 0-100 (toward neighbors/siblings)
    shame: float = 10.0            # 0-100 (economic status)
    attachment: Dict[str, float] = field(default_factory=dict)  # love to family members
    
    def get_dominant_emotion(self) -> EmotionalState:
        """Which emotion is most intense?"""
        emotions = {
            "stress": self.stress,
            "boredom": self.boredom,
            "jealousy": self.jealousy,
            "shame": self.shame,
            "fatigue": self.fatigue,
            "happiness": self.happiness,
        }
        max_emotion = max(emotions, key=emotions.get)
        
        if emotions[max_emotion] < 40:
            return EmotionalState.CONTENT
        
        return EmotionalState[max_emotion.upper()]

@dataclass
class Aspiration:
    """Long-term life goals"""
    name: str
    priority: float  # 0-1
    current_progress: float  # 0-1
    cost_to_achieve: float
    years_to_complete: int
    
    # Examples:
    # - "Save for vacation" (priority: 0.3, cost: 2000₾)
    # - "Buy car" (priority: 0.7, cost: 15000₾)
    # - "Move to Saburtalo" (priority: 0.6, cost: 200000₾)
    # - "Send child to private school" (priority: 0.9, cost: 5000₾/year)

@dataclass
class Identity:
    """Who is this agent in society?"""
    archetype: str  # "health_conscious_mother", "status_seeker", "traditionalist", etc.
    
    # Behavioral traits
    risk_aversion: float       # 0=risk_taker, 1=careful
    materialism: float         # 0=minimalist, 1=brand_conscious
    sociability: float         # 0=hermit, 1=extrovert
    tradition_adherence: float # 0=modern, 1=traditional
    
    # This radically changes behavior
    # "health_conscious_mother" will buy expensive organic food despite budget
    # "status_seeker" will buy expensive brands for prestige
    # "traditionalist" will insist on Georgian food and family gatherings

@dataclass
class Habit:
    """Recurring patterns (often irrational)"""
    name: str
    frequency: str  # "daily", "weekly", "monthly"
    cost: float     # 0 if free
    emotional_relief: float  # 0-1, how much does it reduce boredom/stress
    irrationality: float  # 0-1, how much does this violate economic rationality
    
    # Examples:
    # - Expensive coffee (daily, cost: 3₾, irrationality: 0.8)
    # - Scrolling TikTok (daily, free, relief: 0.5)
    # - Weekly supra with friends (weekly, cost: 50₾, relief: 0.9)
    # - Buying comfort clothes (monthly, cost: 40₾, irrationality: 0.7)

class LifeRoutineEngine:
    """Manages daily/weekly/monthly routines"""
    
    def __init__(self, agent):
        self.agent = agent
        self.current_hour = 0
        self.current_day_of_week = 0
        self.current_day_of_month = 0
        
    def get_activity_for_hour(self, hour: int, day_of_week: int) -> Tuple[ActivityType, float]:
        """
        What is this agent doing at this hour?
        Returns: (ActivityType, enjoyment_value 0-1)
        """
        # Age-based differences
        is_child = self.agent.age < 18
        is_parent = self.agent.age > 30
        is_elderly = self.agent.age > 60
        
        # Work/School hours (9-17)
        if 9 <= hour < 17:
            if is_child and hour < 15:  # School
                return ActivityType.SCHOOL, 0.4  # kids don't love school
            elif not is_elderly and self.agent.has_job:
                return ActivityType.WORK, 0.3  # most people don't love work
            else:
                return ActivityType.LEISURE, 0.5
        
        # Sleep (23-07)
        elif hour in [23, 0, 1, 2, 3, 4, 5, 6]:
            return ActivityType.SLEEP, 0.7
        
        # Family breakfast (7-8)
        elif 7 <= hour < 9:
            return ActivityType.EATING, 0.6
        
        # Lunch (12-13)
        elif 12 <= hour < 13:
            return ActivityType.EATING, 0.5
        
        # Evening family time (18-20)
        elif 18 <= hour < 20:
            activity = ActivityType.FAMILY_TIME if random.random() > 0.3 else ActivityType.EATING
            return activity, 0.7
        
        # Social/leisure time (20-23)
        elif 20 <= hour < 23:
            # Weighted choice: scrolling vs socializing vs exercise
            activities = [
                (ActivityType.SCROLLING, 0.5 if self.agent.age < 25 else 0.3),
                (ActivityType.SOCIALIZING, 0.7),
                (ActivityType.EXERCISE, 0.6 if self.agent.identity.health_conscious else 0.2),
            ]
            chosen = random.choices([a[0] for a in activities], [a[1] for a in activities])[0]
            enjoyment = next(a[1] for a in activities if a[0] == chosen)
            return chosen, enjoyment
        
        # Default leisure
        return ActivityType.LEISURE, 0.5
    
    def update_emotions_from_activity(self, activity: ActivityType, enjoyment: float):
        """Activity influences emotional state"""
        
        if activity == ActivityType.WORK:
            self.agent.emotions.stress += 5 * (1 - enjoyment)
            self.agent.emotions.fatigue += 10
        
        elif activity == ActivityType.SLEEP:
            self.agent.emotions.fatigue -= 15
            self.agent.emotions.stress -= 5
        
        elif activity == ActivityType.SCROLLING:
            self.agent.emotions.boredom -= 10
            if self.agent.emotions.jealousy < 50:
                self.agent.emotions.jealousy += 5  # Comparing to others
        
        elif activity == ActivityType.SOCIALIZING:
            self.agent.emotions.happiness += 15
            self.agent.emotions.boredom -= 20
            self.agent.emotions.stress -= 5
        
        elif activity == ActivityType.FAMILY_TIME:
            self.agent.emotions.happiness += 10
            self.agent.emotions.stress -= 10
        
        elif activity == ActivityType.EXERCISE:
            self.agent.emotions.stress -= 8
            self.agent.emotions.happiness += 5
            self.agent.emotions.fatigue += 3

class SocialInfluenceEngine:
    """Neighborhood gossip, trends, recommendations"""
    
    def __init__(self, model):
        self.model = model
        self.gossip_topics = {}  # What are people talking about?
    
    def spread_store_recommendation(self, from_agent, to_agent, store_name: str, reason: str):
        """
        'Magniti is cheaper than Spar' spreads through neighborhood
        This RADICALLY affects shopping behavior
        """
        if random.random() < 0.7:  # 70% chance gossip sticks
            to_agent.store_loyalty[store_name] += 0.2
            print(f"💬 {from_agent.name} → {to_agent.name}: '{reason}'")
    
    def spread_trend(self, trend_name: str, affected_agents: list, strength: float = 0.5):
        """
        Trend from TikTok affects buying preferences
        e.g., "everyone wants mango juice"
        """
        for agent in affected_agents:
            print(f"📱 Trend '{trend_name}' affects {agent.name}")
    
    def spread_aspirations(self, from_agent, to_agent, aspiration_name: str):
        """
        If neighbor buys car, others want car too
        Status competition drives economy
        """
        if aspiration_name not in [a.name for a in to_agent.aspirations]:
            to_agent.aspirations.append(Aspiration(
                name=aspiration_name,
                priority=random.uniform(0.3, 0.7),
                current_progress=0,
                cost_to_achieve=random.uniform(5000, 50000),
                years_to_complete=random.randint(2, 10)
            ))
            print(f"🎯 {to_agent.name} now wants: {aspiration_name}")

class CultureEngine:
    """Georgian cultural rituals and obligations"""
    
    GEORGIAN_HOLIDAYS = [
        {"month": 1, "day": 1, "name": "New Year", "type": "family", "cost": 200},
        {"month": 3, "day": 8, "name": "Women's Day", "type": "gifting", "cost": 100},
        {"month": 5, "day": 9, "name": "Victory Day", "type": "national", "cost": 50},
        {"month": 10, "day": 14, "name": "Svetitskoba", "type": "religious", "cost": 100},
        {"month": 11, "day": 26, "name": "Georgian Independence", "type": "national", "cost": 50},
    ]
    
    def check_upcoming_obligation(self, current_month: int, current_day: int) -> Optional[Dict]:
        """Is there a cultural obligation this month?"""
        for holiday in self.GEORGIAN_HOLIDAYS:
            if (holiday["month"] == current_month and 
                abs(current_day - holiday["day"]) <= 3):  # 3 days before
                return holiday
        return None
    
    def apply_supra_obligation(self, agent, family_member_visiting: bool = False):
        """
        Supra = Georgian feast = must-do social event
        This OVERRIDES budget considerations
        """
        supra_cost = random.uniform(100, 300)  # ₾
        
        # Even if poor, you host supra for family/guests
        if agent.household.budget >= supra_cost or family_member_visiting:
            agent.household.budget -= supra_cost
            agent.emotions.happiness += 20
            agent.emotions.stress -= 10
            print(f"🍽️ {agent.name} hosted supra (cost: ₾{supra_cost:.0f})")
            return True
        
        # If too poor, still shame of not hosting properly
        agent.emotions.shame += 15
        return False

# Example Georgian Family Identity Archetypes
GEORGIAN_ARCHETYPES = {
    "health_conscious_mother": {
        "risk_aversion": 0.7,
        "materialism": 0.3,
        "sociability": 0.6,
        "tradition_adherence": 0.4,
        "preferred_foods": ["organic", "fresh", "homemade"],
        "willing_to_pay_premium_for": ["child_education", "health_products", "vegetables"],
    },
    "traditional_grandfather": {
        "risk_aversion": 0.8,
        "materialism": 0.2,
        "sociability": 0.7,
        "tradition_adherence": 0.95,
        "preferred_foods": ["georgian_traditional", "homemade"],
        "willing_to_pay_premium_for": ["family_events", "alcohol_quality"],
    },
    "status_seeking_young_professional": {
        "risk_aversion": 0.4,
        "materialism": 0.85,
        "sociability": 0.9,
        "tradition_adherence": 0.2,
        "preferred_foods": ["cafe", "international", "trendy"],
        "willing_to_pay_premium_for": ["brand_clothes", "phone", "car"],
    },
    "practical_parent": {
        "risk_aversion": 0.6,
        "materialism": 0.4,
        "sociability": 0.5,
        "tradition_adherence": 0.5,
        "preferred_foods": ["affordable", "filling"],
        "willing_to_pay_premium_for": ["child_needs", "emergency_funds"],
    },
}
