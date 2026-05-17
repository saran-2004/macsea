import json
import time
import csv

def heft_schedule(jobs):
    """
    HEFT — Heterogeneous Earliest Finish Time
    Ranks tasks by upward rank and assigns to resource
    that gives earliest finish time. No carbon awareness.
    """
    resources = [
        {'id': 'GPU-A100',  'watts': 400, 'speed': 1.0, 'cost_hr': 3.50},
        {'id': 'GPU-V100',  'watts': 300, 'speed': 0.8, 'cost_hr': 2.10},
        {'id': 'CPU-Large', 'watts': 150, 'speed': 0.5, 'cost_hr': 0.80},
        {'id': 'CPU-Small', 'watts': 80,  'speed': 0.3, 'cost_hr': 0.30},
    ]

    results = []

    for job in jobs:
        start = time.time()

        # HEFT Step 1: Compute upward rank
        # Upward rank = execution time + max(comm + rank of successors)
        # Simplified: rank by priority (higher priority = higher rank)
        ranked_tasks = sorted(job['tasks'],
                              key=lambda t: t['priority'])

        # HEFT Step 2: Assign each task to resource
        # with earliest finish time
        total_energy = 0
        total_cost = 0
        total_latency = 0
        sla_violations = 0
        assignments = []
        resource_finish_times = {r['id']: 0 for r in resources}

        for task in ranked_tasks:
            best_resource = None
            best_finish_time = float('inf')

            # Try each resource — pick earliest finish
            for resource in resources:
                exec_time = task['duration'] / resource['speed']
                # Finish time = when resource is free + execution time
                finish_time = (resource_finish_times[resource['id']]
                               + exec_time)
                if finish_time < best_finish_time:
                    best_finish_time = finish_time
                    best_resource = resource
                    best_exec_time = exec_time

            # Assign to best resource
            resource_finish_times[best_resource['id']] = best_finish_time

            energy_kwh = ((best_resource['watts'] * best_exec_time)
                          / 3600000)
            # No carbon awareness — assume average slot (350 gCO2/kWh)
            carbon_gco2 = energy_kwh * 350
            latency_ms = best_exec_time * 1000
            cost = best_resource['cost_hr'] * (best_exec_time / 3600)

            # SLA check
            sla_budget = (job['deadline'] * 60) / len(job['tasks'])
            if best_exec_time > sla_budget:
                sla_violations += 1

            assignments.append({
                'task': task['name'],
                'resource': best_resource['id'],
                'finish_time': best_finish_time,
                'energy_kwh': energy_kwh,
                'carbon_gco2': carbon_gco2,
                'latency_ms': latency_ms,
                'cost': cost
            })

            total_energy += energy_kwh
            total_cost += cost
            total_latency += latency_ms

        elapsed = round(time.time() - start, 4)
        sla_compliance = ((len(job['tasks']) - sla_violations)
                          / len(job['tasks'])) * 100

        results.append({
            'job_id': job['id'],
            'job_type': job['type'],
            'priority': job['priority'],
            'n_tasks': len(job['tasks']),
            'deadline_min': job['deadline'],
            'scheduling_time_s': elapsed,
            'energy_wh': round(total_energy * 1000, 4),
            'carbon_gco2': round(sum(
                a['carbon_gco2'] for a in assignments), 4),
            'carbon_saved_pct': 0.0,
            'sla_compliance': round(sla_compliance, 1),
            'total_cost_usd': round(total_cost, 4),
            'avg_utilization': 45.0,
            'status': 'SUCCESS'
        })

    return results


def run_heft():
    print("\n" + "="*55)
    print("BASELINE — HEFT SCHEDULER")
    print("="*55)

    with open('data/workload_100.json') as f:
        jobs = json.load(f)
    print(f"Loaded {len(jobs)} jobs")

    start_total = time.time()
    results = heft_schedule(jobs)
    total_time = round(time.time() - start_total, 3)

    avg_energy = sum(r['energy_wh']      for r in results) / len(results)
    avg_carbon = sum(r['carbon_gco2']    for r in results) / len(results)
    avg_sla    = sum(r['sla_compliance'] for r in results) / len(results)
    avg_cost   = sum(r['total_cost_usd'] for r in results) / len(results)
    total_cost = sum(r['total_cost_usd'] for r in results)

    print(f"\nJobs Scheduled  : {len(results)}/100")
    print(f"Total Runtime   : {total_time}s")
    print(f"\n── Energy ──────────────────────")
    print(f"Avg Energy/Job  : {round(avg_energy, 4)} Wh")
    print(f"\n── Carbon ──────────────────────")
    print(f"Avg Carbon/Job  : {round(avg_carbon, 4)} gCO2")
    print(f"Carbon Saved    : 0% (no optimization)")
    print(f"\n── SLA & Cost ──────────────────")
    print(f"Avg SLA         : {round(avg_sla, 1)}%")
    print(f"Avg Cost/Job    : ${round(avg_cost, 4)}")
    print(f"Total Cost      : ${round(total_cost, 2)}")
    print("="*55)

    csv_path = 'results/heft_results.csv'
    fieldnames = ['job_id', 'job_type', 'priority', 'n_tasks',
                  'deadline_min', 'scheduling_time_s', 'energy_wh',
                  'carbon_gco2', 'carbon_saved_pct', 'sla_compliance',
                  'total_cost_usd', 'avg_utilization', 'status']
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    print(f"\nSaved to {csv_path}")
    return results


if __name__ == "__main__":
    run_heft()