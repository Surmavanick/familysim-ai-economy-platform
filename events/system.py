"""
Economic and social events system for the simulation.
Implements real-world economic shocks and opportunities.
"""
import random
from datetime import datetime
from typing import List, Dict, Any
from world.tbilisi_geography import GEORGIAN_ECONOMIC_EVENTS


class Event:
    """Represents an economic or social event."""
    
    def __init__(self, name: str, event_type: str, **details):
        self.name = name
        self.event_type = event_type  # income, expense, opportunity, inflation, cultural
        self.details = details
        self.timestamp = None
        self.affected_agents = []
    
    def apply(self, agent, model):
        """Apply event effects to an agent."""
        if self.event_type == "income":
            amount = self.details.get("amount", 0)
            agent.model.households[agent.household_id].budget += amount
            agent.add_memory(f"Received {self.name}: ₾{amount:.2f}")
            return amount
        
        elif self.event_type == "expense":
            amount = self.details.get("amount", 0)
            household = agent.model.households[agent.household_id]
            if household.budget >= amount:
                household.budget -= amount
                agent.add_memory(f"Paid for {self.name}: -₾{amount:.2f}")
            else:
                agent.stress += 10
                agent.add_memory(f"Could not afford {self.name}")
            return amount
        
        elif self.event_type == "inflation":
            rate = self.details.get("rate", 1.05)
            agent.model.market.apply_global_inflation(rate - 1)
            agent.add_memory(f"Economy: {self.name} - prices up {(rate-1)*100:.1f}%")
            return rate
        
        elif self.event_type == "opportunity":
            bonus = self.details.get("bonus", 0)
            if agent.role != "child":
                agent.accrued_salary *= (1 + bonus)
                agent.add_memory(f"Opportunity: {self.name} - salary bonus +{bonus*100:.0f}%")


class EventsEngine:
    """Manages all economic and social events in the simulation."""
    
    def __init__(self, model):
        self.model = model
        self.events_log = []
        self.month_events_processed = set()  # Track which events processed this month
    
    def process_monthly_events(self):
        """Process all events that should trigger this month."""
        current_month = self.model.current_time.month
        current_day = self.model.current_time.day
        
        # Only process once per month (on day 1)
        if current_day != 1 or current_month in self.month_events_processed:
            return
        
        self.month_events_processed.add(current_month)
        
        # Process each defined event
        for event_def in GEORGIAN_ECONOMIC_EVENTS:
            # Check if event triggers this month
            trigger_months = event_def.get("trigger_months", [])
            if current_month not in trigger_months:
                continue
            
            # Check probability
            probability = event_def.get("probability", 1.0)
            if random.random() > probability:
                continue
            
            self._apply_event(event_def)
    
    def process_random_events(self):
        """Process random events (health emergency, job loss, etc)."""
        # 10% chance of random event per day
        if random.random() > 0.10:
            return
        
        random_events = [
            {
                "name": "Healthcare Emergency",
                "type": "expense",
                "amount": random.uniform(200, 800),
                "description": "Unexpected medical cost",
                "probability": 0.05
            },
            {
                "name": "Unexpected Job Loss",
                "type": "crisis",
                "description": "Family member loses job",
                "probability": 0.02
            },
            {
                "name": "Bonus Payment",
                "type": "income",
                "amount": random.uniform(200, 500),
                "description": "Work bonus or gift",
                "probability": 0.08
            },
            {
                "name": "Car Repair",
                "type": "expense",
                "amount": random.uniform(300, 1000),
                "description": "Vehicle maintenance",
                "probability": 0.03
            }
        ]
        
        for event_def in random_events:
            if random.random() < event_def.get("probability", 0.01):
                self._apply_event(event_def)
    
    def _apply_event(self, event_def: Dict):
        """Apply an event definition to affected agents/households."""
        event_name = event_def.get("name", "Unknown Event")
        event_type = event_def.get("type", "general")
        
        # Determine affected agents
        target_roles = event_def.get("target_roles", None)
        affected_agents = self._get_affected_agents(target_roles)
        
        if not affected_agents:
            return
        
        # Log event
        event_log_entry = {
            "timestamp": str(self.model.current_time),
            "event": event_name,
            "type": event_type,
            "agents_affected": len(affected_agents),
            "details": event_def
        }
        self.events_log.append(event_log_entry)
        
        # Apply to each affected agent
        for agent in affected_agents:
            self._apply_single_agent_event(agent, event_def)
        
        # Global logging for significant events
        if len(affected_agents) > 5 or event_type in ["inflation", "crisis"]:
            print(f"[EVENT] {event_name} - Affected {len(affected_agents)} people")
    
    def _get_affected_agents(self, target_roles: List[str] = None) -> List:
        """Get agents affected by an event."""
        agents = list(self.model.schedule.agents)
        
        if target_roles:
            agents = [a for a in agents if a.role in target_roles]
        
        return agents
    
    def _apply_single_agent_event(self, agent, event_def: Dict):
        """Apply event effects to a single agent."""
        event_type = event_def.get("type", "general")
        
        if event_type == "income":
            amount = event_def.get("amount", 0)
            self.model.households[agent.household_id].budget += amount
            agent.add_memory(f"Income event: {event_def.get('name')} +₾{amount:.2f}")
        
        elif event_type == "expense":
            amount = event_def.get("amount", 0)
            household = self.model.households[agent.household_id]
            if household.budget >= amount:
                household.budget -= amount
            else:
                agent.stress += 15  # Financial stress
            agent.add_memory(f"Expense: {event_def.get('name')} -₾{amount:.2f}")
        
        elif event_type == "inflation":
            rate = event_def.get("rate", 1.05)
            agent.add_memory(f"Inflation noticed: prices up {(rate-1)*100:.1f}%")
            agent.fun -= 5  # Frustration
        
        elif event_type == "crisis":
            agent.stress += 25
            agent.health -= 10
            agent.add_memory(f"Crisis event: {event_def.get('name')}")
        
        elif event_type == "opportunity":
            agent.fun += 10
            agent.stress -= 5
            agent.add_memory(f"Good news: {event_def.get('name')}")
    
    def get_event_summary(self) -> Dict:
        """Get summary of all events that occurred."""
        summary = {
            "total_events": len(self.events_log),
            "by_type": {},
            "unique_events": set()
        }
        
        for event_entry in self.events_log:
            event_name = event_entry["event"]
            event_type = event_entry["type"]
            
            if event_type not in summary["by_type"]:
                summary["by_type"][event_type] = 0
            summary["by_type"][event_type] += 1
            summary["unique_events"].add(event_name)
        
        summary["unique_events"] = list(summary["unique_events"])
        return summary
