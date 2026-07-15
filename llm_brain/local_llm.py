"""
Local LLM interface for agent reasoning.
Supports both Ollama (if installed) and fallback heuristic reasoning.
"""
import requests
import json
from typing import Optional, Dict, Any


class LocalLLMInterface:
    """Interface for local LLM reasoning - uses Ollama or heuristic fallback."""
    
    def __init__(self, model_name: str = "qwen2.5:3b", use_ollama: bool = True):
        self.model_name = model_name
        self.use_ollama = use_ollama
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_available = self._check_ollama()
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        if not self.use_ollama:
            return False
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                print(f"✓ Ollama server detected | Model: {self.model_name}")
                return True
        except:
            print("✓ Ollama not available - using heuristic reasoning fallback")
            return False
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Generate agent reasoning given a context prompt.
        Returns the agent's decision/thought.
        """
        if self.ollama_available:
            return self._ollama_think(prompt, context)
        else:
            return self._heuristic_think(prompt, context)
    
    def _ollama_think(self, prompt: str, context: Dict[str, Any]) -> str:
        """Call Ollama for reasoning with optimized parameters."""
        # Create minimal prompt for CPU efficiency
        stress = context.get("stress", 0)
        budget = context.get("budget", 0)
        role = context.get("role", "")
        triggers = context.get("triggers", [])
        
        # Ultra-short prompt format
        short_prompt = f"S:{stress:.0f} B:{budget:.0f} R:{role[:3]}. Act:"
        
        payload = {
            "model": self.model_name,
            "prompt": short_prompt,
            "stream": False,
            "temperature": 0.3,  # Lower temp = faster + more deterministic
            "top_k": 30,
            "top_p": 0.8,
            "num_predict": 15,  # Very short output
            "num_ctx": 256,     # Minimal context
            "num_threads": 4
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=3)
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "").strip()[:30]
                return llm_response if llm_response else "NEUTRAL"
        except requests.exceptions.Timeout:
            pass  # Silent fail
        except Exception:
            pass  # Silent fail
        
        return self._heuristic_think(prompt, context)
    
    def _heuristic_think(self, prompt: str, context: Dict[str, Any]) -> str:
        """Fallback heuristic-based reasoning without LLM."""
        if not context:
            return "NEUTRAL"
        
        stress = context.get("stress", 0)
        budget = context.get("budget", 0)
        inventory = context.get("inventory_size", 0)
        role = context.get("role", "")
        triggers = context.get("triggers", [])
        
        # Decision logic based on context
        if "high_stress" in triggers and stress > 80:
            if "impulsivity" in context.get("personality", {}) and context["personality"]["impulsivity"] > 0.6:
                return "IMPULSE_BUY"
            else:
                return "STRESS_COPING"
        
        if "low_budget" in triggers and budget < 500:
            if role == "father" or role == "mother":
                return "EMERGENCY_PLAN"
            return "ANXIOUS"
        
        if inventory < 7:
            return "RESTOCK_NEEDED"
        
        if stress < 20 and budget > 2000:
            return "LEISURE_SPENDING"
        
        return "DAILY_ROUTINE"


class ReasoningPrompts:
    """Template prompts for agent reasoning - optimized for qwen2.5:3b."""
    
    @staticmethod
    def financial_decision(agent_name: str, budget: float, inventory_size: int) -> str:
        prompt = f"""Agent {agent_name} in Tbilisi.
Budget: ₾{budget:.0f}. Food items: {inventory_size}.
Decision: Spend or save? (Keep response to 1-2 words)"""
        return prompt
    
    @staticmethod
    def stress_decision(agent_name: str, stress_level: float, reason: str) -> str:
        prompt = f"""{agent_name} - Stress: {stress_level:.0f}/100 ({reason})
Coping strategy? (1-2 words)"""
        return prompt
    
    @staticmethod
    def social_decision(agent_name: str, relationship_status: str, other_agent: str) -> str:
        prompt = f"""{agent_name} & {other_agent}: relationship is {relationship_status}.
Action? (strengthen/avoid/neutral/conflict)"""
        return prompt
