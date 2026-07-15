
import random

class ReasoningEngine:
    def __init__(self, model):
        self.model = model

    def evaluate_thinking_need(self, agent):
        """
        Criteria for selective cognition:
        1. High stress (> 80)
        2. Low household budget (< 10% of start)
        3. Significant relationship change
        4. Inflation/Price shock (future)
        """
        household = self.model.households[agent.household_id]
        
        triggers = []
        if agent.stress > 70: triggers.append("high_stress")
        if household.budget < 400: triggers.append("low_budget")
        
        if triggers:
            return self.generate_reasoning_prompt(agent, household, triggers)
        return None

    def generate_reasoning_prompt(self, agent, household, triggers):
        # This context would be passed to an LLM
        context = {
            "agent": agent.name,
            "role": agent.role,
            "stress": agent.stress,
            "budget": household.budget,
            "inventory_size": len(household.inventory),
            "triggers": triggers,
            "recent_memories": agent.memory_events[-5:]
        }
        
        # Placeholder for LLM call
        # print(f"DEBUG: Reasoning triggered for {agent.name} | Triggers: {triggers}")
        
        return context

    def process_decision(self, agent, context):
        # Here an LLM would return a decision. 
        # For now, we simulate a decision based on the triggers.
        if "low_budget" in context['triggers']:
            # Decision: Austerity measure
            agent.personality['frugality'] = min(1.0, agent.personality['frugality'] + 0.1)
            agent.add_memory("Decided to be more frugal due to family financial crisis.")
            return "AUSTERITY"
        
        return "NONE"
