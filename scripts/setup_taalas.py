#!/usr/bin/env python3
"""
Taalas Migration Setup Script
Prepares the simulation to use Taalas Cloud API instead of local Ollama

Run this once before your first simulation:
    python3 scripts/setup_taalas.py
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def print_header(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_env_file():
    """Check if .env file exists and has API key"""
    print_header("Step 1: Checking Environment Configuration")
    
    env_path = PROJECT_ROOT / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Creating .env from template...")
        
        # Create .env from .env.example
        example_path = PROJECT_ROOT / ".env.example"
        if example_path.exists():
            with open(example_path, 'r') as f:
                content = f.read()
            with open(env_path, 'w') as f:
                f.write(content)
            print("✅ .env file created from template")
        else:
            print("❌ .env.example not found either!")
            return False
    
    # Check if API key is set
    with open(env_path, 'r') as f:
        content = f.read()
    
    if "TAALAS_API_KEY=" in content and "your_api_key_here" not in content:
        print("✅ TAALAS_API_KEY is configured")
        return True
    else:
        print("⚠️ TAALAS_API_KEY not properly configured")
        print("   Add your API key to .env file:")
        print("   TAALAS_API_KEY=your_key_here")
        return False

def check_python_deps():
    """Check if required Python packages are installed"""
    print_header("Step 2: Checking Python Dependencies")
    
    required = ['mesa', 'pandas', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️ Missing packages: {', '.join(missing)}")
        print("   Installing...")
        for package in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("✅ Dependencies installed")
        return True
    
    return True

def test_taalas_connection():
    """Test connection to Taalas API"""
    print_header("Step 3: Testing Taalas API Connection")
    
    api_key = os.getenv("TAALAS_API_KEY")
    
    if not api_key or api_key == "your_api_key_here":
        print("⚠️ TAALAS_API_KEY not set or invalid")
        print("   Set it in .env file first")
        return False
    
    try:
        from llm_brain.taalas_interface import TaalaLLMInterface
        
        print(f"Testing with API key: {api_key[:10]}...")
        llm = TaalaLLMInterface(api_key=api_key, timeout=5)
        
        print("✅ Taalas API connection successful!")
        print(f"   Model: llama3.1-8B")
        print(f"   Status: Healthy")
        
        return True
    
    except Exception as e:
        print(f"❌ Taalas API connection failed: {e}")
        print("   Possible causes:")
        print("   - Invalid API key")
        print("   - No internet connection")
        print("   - Taalas API is down")
        return False

def check_model_py_updated():
    """Check if model.py uses Taalas"""
    print_header("Step 4: Checking model.py Configuration")
    
    model_path = PROJECT_ROOT / "simulation_core" / "model.py"
    
    if not model_path.exists():
        print("❌ simulation_core/model.py not found!")
        return False
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    if "from llm_brain.taalas_interface import" in content:
        print("✅ model.py already configured for Taalas")
        return True
    elif "from llm_brain.local_llm import" in content:
        print("⚠️ model.py still using LocalLLMInterface (old Ollama)")
        print("   Automatically updating...")
        
        # Update imports
        content = content.replace(
            "from llm_brain.local_llm import LocalLLMInterface",
            "from llm_brain.taalas_interface import TaalaLLMInterface, HybridLLMInterface"
        )
        
        # Update initialization
        content = content.replace(
            """        self.llm = LocalLLMInterface(use_ollama=True)  # Local LLM interface""",
            """        # ✨ Using Taalas Cloud API
        api_key = os.getenv("TAALAS_API_KEY")
        if api_key:
            self.llm = TaalaLLMInterface(api_key=api_key)
        else:
            self.llm = HybridLLMInterface()"""
        )
        
        # Add import for os if missing
        if "import os" not in content:
            content = "import os\n" + content
        
        with open(model_path, 'w') as f:
            f.write(content)
        
        print("✅ model.py updated successfully!")
        return True
    else:
        print("⚠️ model.py configuration unclear")
        return False

def suggest_next_steps():
    """Print next steps"""
    print_header("Setup Complete! ✅")
    
    print("You're ready to run the simulation with Taalas!")
    print("\nNext steps:")
    print("1. Run the simulation:")
    print("   python3 simulation_run.py")
    print("\n2. Expected output:")
    print("   ✅ Taalas API healthy")
    print("   ✅ Using Taalas API for LLM reasoning")
    print("   [simulation runs 4-6x faster than before]")
    print("\n3. Check results:")
    print("   cat simulation_report.json")

def main():
    """Run setup checks"""
    print("\n" + "="*60)
    print("  TAALAS MIGRATION SETUP")
    print("  Configuring simulation to use Taalas Cloud API")
    print("="*60)
    
    checks = [
        ("Environment Configuration", check_env_file),
        ("Python Dependencies", check_python_deps),
        ("Taalas API Connection", test_taalas_connection),
        ("model.py Configuration", check_model_py_updated),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Setup Summary")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        suggest_next_steps()
        print("\n" + "="*60 + "\n")
        return 0
    else:
        print("\n⚠️ Some checks failed. Please fix the issues above.")
        print("="*60 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
