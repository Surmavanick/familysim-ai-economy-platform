
from simulation_core.model import FamilySimulation
from simulation_core.population import generate_population
from results.report_generator import generate_simulation_report, print_report
import time

def run_society_simulation():
    print("====================================================")
    print("FAMILYSIM: Large-Scale Synthetic Society Simulation")
    print("====================================================")
    
    # Generate 500 families (approx 1,500-2,000 agents) distributed across
    # Tbilisi. A larger sample lowers per-capita sampling noise before the
    # report extrapolates it to a target city-scale population (Path B
    # market-sizing — see _TARGET_POPULATION in report_generator.py).
    population = generate_population(n=500)
    
    model = FamilySimulation(population)
    
    total_ticks = 30 * 24 # 30 days
    
    for i in range(total_ticks):
        # Income is handled inside model.step() (weekly payday on Sundays).
        model.step()
        
    print("\n====================================================")
    print("SOCIETY SIMULATION COMPLETE")
    print("====================================================")
    
    # Generate and display results report
    report = generate_simulation_report(model)
    print_report(report)

if __name__ == "__main__":
    run_society_simulation()
