import ray

@ray.remote
class EnergyOptimizationAgent:

    def __init__(self):
        self.name = "Energy Optimization Agent"
        print(f"[EOA] Agent initialized")

    def optimize(self, planned_job):
        print(f"[EOA] Optimizing energy for job: {planned_job['job_id']}")

        # Available resources with power profiles
        resources = [
            {'id': 'GPU-A100',  'watts': 400, 'speed': 1.0, 'type': 'GPU'},
            {'id': 'GPU-V100',  'watts': 300, 'speed': 0.8, 'type': 'GPU'},
            {'id': 'CPU-Large', 'watts': 150, 'speed': 0.5, 'type': 'CPU'},
            {'id': 'CPU-Small', 'watts': 80,  'speed': 0.3, 'type': 'CPU'},
        ]

        assignments = []
        total_energy = 0

        for task in planned_job['planned_tasks']:
            # Pick resource with best energy efficiency
            # Energy = watts × duration / speed
            best = min(resources, key=lambda r: (
                r['watts'] * task['duration'] / r['speed']
            ))

            actual_duration = task['duration'] / best['speed']
            energy_kwh = (best['watts'] * actual_duration) / 3600000

            assignments.append({
                'task': task['name'],
                'resource': best['id'],
                'watts': best['watts'],
                'duration_s': round(actual_duration, 1),
                'energy_kwh': round(energy_kwh, 6)
            })
            total_energy += energy_kwh

        result = {
            'job_id': planned_job['job_id'],
            'agent': self.name,
            'assignments': assignments,
            'total_energy_kwh': round(total_energy, 6),
            'status': 'OPTIMIZED'
        }

        print(f"[EOA] Done — total energy: {round(total_energy*1000, 4)} Wh")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    # Simulated output from WPA (Agent 1)
    planned_job = {
        'job_id': 'JOB-001',
        'planned_tasks': [
            {'name': 'preprocess_data',  'priority': 1, 'duration': 10},
            {'name': 'train_model',      'priority': 2, 'duration': 45},
            {'name': 'validate_model',   'priority': 3, 'duration': 15},
            {'name': 'generate_report',  'priority': 4, 'duration': 5},
        ]
    }

    agent = EnergyOptimizationAgent.remote()
    result = ray.get(agent.optimize.remote(planned_job))

    print("\n" + "="*50)
    print("ENERGY OPTIMIZATION AGENT — RESULTS")
    print("="*50)
    print(f"Job ID       : {result['job_id']}")
    print(f"Total Energy : {result['total_energy_kwh']} kWh "
          f"({round(result['total_energy_kwh']*1000, 4)} Wh)")
    print(f"Status       : {result['status']}")
    print("\nTask assignments:")
    for a in result['assignments']:
        print(f"  {a['task']:<20} → {a['resource']:<12} "
              f"| {a['watts']}W | {a['duration_s']}s "
              f"| {a['energy_kwh']} kWh")

    ray.shutdown()