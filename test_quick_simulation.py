"""
Quick test simulation - 3 days to verify LLM integration.
"""
from simulation_core.model import FamilySimulation
from simulation_core.population import generate_population
from results.report_generator import generate_simulation_report, print_report

def run_quick_test():
    print("====================================================")
    print("QUICK TEST: 3-Day Simulation with qwen2.5:3b LLM")
    print("====================================================")
    
    # Generate only 10 families for quick test
    population = generate_population(n=10)
    
    model = FamilySimulation(population)
    
    total_ticks = 3 * 24  # 3 days instead of 30
    
    for i in range(total_ticks):
        model.step()
        
    print("\n====================================================")
    print("QUICK TEST COMPLETE")
    print("====================================================")
    
    # Generate report
    report = generate_simulation_report(model)
    print_report(report)

if __name__ == "__main__":
    run_quick_test()
