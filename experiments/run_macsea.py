import ray
import json
import time
import csv
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.wpa  import WorkflowPlanningAgent
from agents.eoa  import EnergyOptimizationAgent
from agents.cera import CarbonReductionAgent
from agents.lma  import LatencyManagementAgent
from agents.draa import DynamicResourceAllocationAgent


def run_single_job(job, wpa, eoa, cera, lma, draa):
    """Run one job through the full MACSEA pipeline."""
    try:
        start = time.time()
        wpa_result  = ray.get(wpa.plan.remote(job))
        eoa_result  = ray.get(eoa.optimize.remote(wpa_result))
        cera_result = ray.get(cera.schedule.remote(eoa_result))
        lma_result  = ray.get(lma.check_and_schedule.remote(cera_result))
        draa_result = ray.get(draa.allocate.remote(lma_result))
        elapsed = round(time.time() - start, 3)

        return {
            'job_id':            job['id'],
            'job_type':          job['type'],
            'priority':          job['priority'],
            'n_tasks':           len(job['tasks']),
            'deadline_min':      job['deadline'],
            'scheduling_time_s': elapsed,
            'energy_wh':         round(eoa_result['total_energy_kwh'] * 1000, 4),
            'carbon_gco2':       cera_result['total_carbon_gco2'],
            'carbon_saved_pct':  cera_result['savings_percent'],
            'best_time_slot':    cera_result['best_time_slot'],
            'sla_compliance':    lma_result['sla_compliance_pct'],
            'escalation':        lma_result['escalation'],
            'total_cost_usd':    draa_result['total_cost_usd'],
            'avg_utilization':   draa_result['avg_utilization_pct'],
            'scale_actions':     len(draa_result['scale_actions']),
            'status':            'SUCCESS'
        }
    except Exception as e:
        return {
            'job_id': job['id'],
            'status': 'FAILED',
            'error':  str(e)
        }


def run_experiment(workload_path='data/workload_100.json'):
    print("\n" + "="*60)
    print("MACSEA — FULL EXPERIMENT RUN")
    print("="*60)

    # Load workload
    with open(workload_path) as f:
        jobs = json.load(f)
    print(f"Loaded {len(jobs)} jobs from {workload_path}")

    # Init Ray and agents
    ray.init(ignore_reinit_error=True)
    print("Launching agents...")
    wpa  = WorkflowPlanningAgent.remote()
    eoa  = EnergyOptimizationAgent.remote()
    cera = CarbonReductionAgent.remote()
    lma  = LatencyManagementAgent.remote()
    draa = DynamicResourceAllocationAgent.remote()

    # Run all jobs
    results = []
    start_total = time.time()

    print(f"\nScheduling {len(jobs)} jobs...\n")
    for i, job in enumerate(jobs):
        result = run_single_job(job, wpa, eoa, cera, lma, draa)
        results.append(result)

        # Progress bar
        pct = (i + 1) / len(jobs)
        bar = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
        print(f"\r  [{bar}] {i+1}/{len(jobs)} jobs", end="", flush=True)

    total_time = round(time.time() - start_total, 2)
    print(f"\n\nAll jobs scheduled in {total_time}s")

    # Filter successful results
    success = [r for r in results if r['status'] == 'SUCCESS']
    failed  = [r for r in results if r['status'] == 'FAILED']

    # Compute summary stats
    avg_energy      = sum(r['energy_wh']        for r in success) / len(success)
    avg_carbon      = sum(r['carbon_gco2']       for r in success) / len(success)
    avg_carbon_saved= sum(r['carbon_saved_pct']  for r in success) / len(success)
    avg_sla         = sum(r['sla_compliance']     for r in success) / len(success)
    avg_cost        = sum(r['total_cost_usd']     for r in success) / len(success)
    avg_util        = sum(r['avg_utilization']    for r in success) / len(success)
    avg_sched_time  = sum(r['scheduling_time_s']  for r in success) / len(success)
    total_cost      = sum(r['total_cost_usd']     for r in success)

    # Print summary
    print("\n" + "="*60)
    print("MACSEA EXPERIMENT RESULTS")
    print("="*60)
    print(f"Jobs Succeeded     : {len(success)}/{len(jobs)}")
    print(f"Jobs Failed        : {len(failed)}")
    print(f"Total Runtime      : {total_time}s")
    print(f"Avg Schedule Time  : {round(avg_sched_time, 3)}s per job")
    print()
    print(f"── Energy ──────────────────────────────")
    print(f"Avg Energy/Job     : {round(avg_energy, 4)} Wh")
    print(f"Total Energy       : {round(avg_energy * len(success), 2)} Wh")
    print()
    print(f"── Carbon ──────────────────────────────")
    print(f"Avg Carbon/Job     : {round(avg_carbon, 4)} gCO2")
    print(f"Avg Carbon Saved   : {round(avg_carbon_saved, 1)}%")
    print(f"Total Carbon       : {round(avg_carbon * len(success), 2)} gCO2")
    print()
    print(f"── SLA & Cost ──────────────────────────")
    print(f"Avg SLA Compliance : {round(avg_sla, 1)}%")
    print(f"Avg Cost/Job       : ${round(avg_cost, 4)}")
    print(f"Total Cost         : ${round(total_cost, 2)}")
    print(f"Avg Utilization    : {round(avg_util, 1)}%")
    print("="*60)

    # Save results to CSV
    csv_path = 'results/macsea_results.csv'
    fieldnames = [
        'job_id', 'job_type', 'priority', 'n_tasks',
        'deadline_min', 'scheduling_time_s', 'energy_wh',
        'carbon_gco2', 'carbon_saved_pct', 'best_time_slot',
        'sla_compliance', 'escalation', 'total_cost_usd',
        'avg_utilization', 'scale_actions', 'status'
    ]
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    print(f"\nResults saved to {csv_path}")
    ray.shutdown()
    return results


if __name__ == "__main__":
    run_experiment()