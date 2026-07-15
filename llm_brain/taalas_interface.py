"""
Taalas API LLM Interface
Cloud-based LLM reasoning for the simulation
Model: llama3.1-8B (more powerful, faster than local qwen2.5:3b)

Features:
- Remote API (no local CPU bottleneck)
- Streaming support
- Better model (llama3.1-8B)
- Faster inference
- Scalable

Usage:
Set TAALAS_API_KEY environment variable, then:
    llm = TaalaLLMInterface()
    response = llm.think("Your prompt here")
"""

import requests
import json
import os
from typing import Optional
import time


class TaalaLLMInterface:
    """
    Interface to Taalas API for LLM-based agent reasoning
    Replaces local Ollama setup with cloud API
    """
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        """
        Initialize Taalas LLM interface
        
        Args:
            api_key: Taalas API key (or use TAALAS_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("TAALAS_API_KEY")
        self.base_url = "https://api.taalas.com"
        self.model = "llama3.1-8B"
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError(
                "Taalas API key not provided. "
                "Set TAALAS_API_KEY environment variable or pass api_key parameter."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Check API health
        self._check_health()
        
        # Stats
        self.requests_made = 0
        self.total_tokens = 0
        self.errors = 0
    
    def _check_health(self):
        """Check if Taalas API is healthy"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            status = response.json()
            print(f"✅ Taalas API healthy: {status['status']}")
            return True
        except Exception as e:
            print(f"⚠️ Taalas API health check failed: {e}")
            return False
    
    def think(self, prompt: str, max_tokens: int = 50) -> str:
        """
        Get reasoning from llama3.1-8B via Taalas API
        
        Args:
            prompt: The prompt to send to LLM
            max_tokens: Maximum tokens in response (default 50 for fast inference)
        
        Returns:
            str: LLM response text
        """
        try:
            # Use chat completion endpoint (more stable)
            payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": self.model,
                "max_tokens": int(max_tokens),
                "temperature": 0.3,  # Low temp for deterministic output
                "stream": False  # For simplicity, non-streaming
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.requests_made += 1
                data = response.json()
                
                # Extract response text
                response_text = data['choices'][0]['message']['content'].strip()
                
                # Track tokens
                if 'usage' in data:
                    self.total_tokens += data['usage'].get('completion_tokens', 0)
                
                return response_text
            
            else:
                self.errors += 1
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                return self._fallback_heuristic(prompt)
        
        except requests.Timeout:
            self.errors += 1
            print(f"⏱️ Taalas API timeout (>{self.timeout}s)")
            return self._fallback_heuristic(prompt)
        
        except Exception as e:
            self.errors += 1
            print(f"❌ Taalas API error: {e}")
            return self._fallback_heuristic(prompt)
    
    def think_streaming(self, prompt: str, max_tokens: int = 50, callback=None):
        """
        Get streaming response from LLM
        Useful for real-time output
        
        Args:
            prompt: The prompt
            max_tokens: Max tokens
            callback: Function to call with each chunk
        
        Yields:
            str: Response chunks
        """
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": self.model,
                "max_tokens": int(max_tokens),
                "temperature": 0.3,
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if 'choices' in data and data['choices']:
                                chunk = data['choices'][0].get('delta', {}).get('content', '')
                                if chunk:
                                    full_response += chunk
                                    if callback:
                                        callback(chunk)
                                    yield chunk
                        except json.JSONDecodeError:
                            pass
            
            self.requests_made += 1
            return full_response
        
        except Exception as e:
            self.errors += 1
            print(f"❌ Streaming error: {e}")
            yield self._fallback_heuristic(prompt)
    
    def _fallback_heuristic(self, prompt: str) -> str:
        """
        Fallback heuristic when API fails
        Simple rules-based reasoning
        """
        print(f"📋 Using fallback heuristic")
        
        # Extract key metrics from prompt
        # Format example: "S:75 B:1500 R:Father. Act:"
        metrics = {}
        
        try:
            # Parse prompt for metrics
            if "S:" in prompt:
                stress = float(prompt.split("S:")[1].split()[0])
                metrics['stress'] = stress
            if "B:" in prompt:
                budget = float(prompt.split("B:")[1].split()[0])
                metrics['budget'] = budget
            if "R:" in prompt:
                role = prompt.split("R:")[1].split(".")[0].strip()
                metrics['role'] = role
        except:
            pass
        
        # Simple heuristic rules
        stress = metrics.get('stress', 50)
        budget = metrics.get('budget', 1500)
        role = metrics.get('role', 'Family Member')
        
        if stress > 75:
            return "IMPULSE_BUY"
        elif budget < 500:
            return "EMERGENCY_PLAN"
        elif stress > 60:
            return "STRESS_RELIEF"
        else:
            return "ROUTINE_SHOPPING"
    
    def get_stats(self) -> dict:
        """Get usage statistics"""
        return {
            "requests_made": self.requests_made,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "error_rate": self.errors / max(1, self.requests_made)
        }
    
    def batch_think(self, prompts: list, max_tokens: int = 50) -> list:
        """
        Process multiple prompts efficiently
        
        Args:
            prompts: List of prompts
            max_tokens: Max tokens per response
        
        Returns:
            list: List of responses
        """
        results = []
        for prompt in prompts:
            results.append(self.think(prompt, max_tokens))
        return results


class HybridLLMInterface:
    """
    Hybrid interface: Try Taalas first, fall back to local reasoning
    Best of both worlds
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize hybrid LLM interface"""
        self.taalas = None
        self.use_taalas = False
        
        try:
            self.taalas = TaalaLLMInterface(api_key)
            self.use_taalas = True
            print("✅ Using Taalas API for LLM reasoning")
        except Exception as e:
            print(f"⚠️ Taalas API not available: {e}")
            print("   Falling back to heuristic reasoning")
    
    def think(self, prompt: str, max_tokens: int = 50) -> str:
        """Think with Taalas if available, else use heuristics"""
        if self.use_taalas and self.taalas:
            return self.taalas.think(prompt, max_tokens)
        else:
            return self._fallback_heuristic(prompt)
    
    def _fallback_heuristic(self, prompt: str) -> str:
        """Fallback heuristic reasoning"""
        # Simple rules
        if "stress" in prompt.lower() and "75" in prompt:
            return "IMPULSE_BUY"
        elif "budget" in prompt.lower() and "500" in prompt:
            return "EMERGENCY_PLAN"
        else:
            return "ROUTINE_SHOPPING"
    
    def get_stats(self) -> dict:
        """Get stats if using Taalas"""
        if self.use_taalas and self.taalas:
            return self.taalas.get_stats()
        return {"mode": "heuristic"}


# ============================================================================
# QUICK TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Test Taalas connection
    api_key = os.getenv("TAALAS_API_KEY")
    
    if not api_key:
        print("❌ TAALAS_API_KEY environment variable not set")
        print("   Usage: export TAALAS_API_KEY='your_key_here'")
        sys.exit(1)
    
    print("🧪 Testing Taalas LLM Interface...\n")
    
    # Initialize
    llm = TaalaLLMInterface(api_key)
    
    # Test prompts
    test_prompts = [
        "S:75 B:1500 R:Father. Act:",
        "S:45 B:3000 R:Mother. Act:",
        "S:90 B:500 R:Child. Act:",
    ]
    
    print("📝 Test Prompts:\n")
    for prompt in test_prompts:
        response = llm.think(prompt, max_tokens=20)
        print(f"Prompt: {prompt}")
        print(f"Response: {response}\n")
    
    # Show stats
    print("📊 Stats:")
    stats = llm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
