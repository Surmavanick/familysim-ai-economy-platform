#!/usr/bin/env python3
"""
TAALAS INTEGRATION - QUICK REFERENCE

Run this anytime for instant setup & testing:
  python3 scripts/quick_start.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def run_cmd(cmd, description):
    """Run command and show status"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    return result.returncode == 0

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║        FAMILYSIM - TAALAS CLOUD INTEGRATION             ║
    ║                                                          ║
    ║        Fast Cloud LLM for Agent Reasoning               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("""
    Choose an option:
    
    1 - Run full setup check
    2 - Test Taalas connection only
    3 - Run 30-day simulation
    4 - Check API health
    5 - Show stats from last run
    6 - Exit
    """)
    
    choice = input("Enter choice (1-6): ").strip()
    
    if choice == '1':
        run_cmd("python3 scripts/setup_taalas.py", "Full Setup Verification")
    
    elif choice == '2':
        run_cmd("""python3 -c "
from llm_brain.taalas_interface import TaalaLLMInterface
import os
api_key = os.getenv('TAALAS_API_KEY')
if api_key:
    llm = TaalaLLMInterface(api_key=api_key, timeout=5)
    response = llm.think('S:75 B:1500 R:Father. Act:', max_tokens=20)
    print(f'✅ Response: {response}')
    stats = llm.get_stats()
    print(f'Stats: {stats}')
else:
    print('❌ TAALAS_API_KEY not set')
        """, "Testing Taalas Connection")
    
    elif choice == '3':
        run_cmd("python3 simulation_run.py", "Running 30-Day Simulation")
        print("""
        
        Next steps:
        1. Check results: cat simulation_report.json
        2. View pretty: python3 -c "import json; print(json.dumps(json.load(open('simulation_report.json')), indent=2)[:500])"
        """)
    
    elif choice == '4':
        run_cmd("""python3 -c "
import requests
print('🏥 Checking Taalas API Health...')
try:
    r = requests.get('https://api.taalas.com/health', timeout=5)
    if r.status_code == 200:
        status = r.json()
        print(f'✅ Status: {status[\"status\"]}')
        print(f'   Queue size: {status.get(\"queue_size\", \"N/A\")}')
    else:
        print(f'⚠️ Status: {r.status_code}')
except Exception as e:
    print(f'❌ Error: {e}')
        """, "API Health Check")
    
    elif choice == '5':
        run_cmd("""python3 -c "
import json
try:
    with open('simulation_report.json') as f:
        report = json.load(f)
    print('📊 Last Simulation Results:')
    print(f'  Duration: {report.get(\"duration_days\", \"N/A\")} days')
    print(f'  Households: {report.get(\"num_households\", \"N/A\")}')
    print(f'  Agents: {report.get(\"total_agents\", \"N/A\")}')
    summary = report.get('economic_summary', {})
    print(f'  Avg Budget: {summary.get(\"avg_household_budget\", \"N/A\"):.0f}₾')
    print(f'  Avg Stress: {summary.get(\"avg_stress\", \"N/A\"):.1f}')
except:
    print('❌ No previous results found')
    print('   Run simulation first: python3 simulation_run.py')
        """, "Show Last Results")
    
    elif choice == '6':
        print("Goodbye! 👋")
        sys.exit(0)
    
    else:
        print("Invalid choice")
        sys.exit(1)

if __name__ == "__main__":
    main()
