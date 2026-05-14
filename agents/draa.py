import ray

@ray.remote
class DynamicResourceAllocationAgent:

    def __init__(self):
        self.name = "Dynamic Resource Allocation Agent"
        self.resources = [
            {'id': 'GPU-A100',  'type': 'GPU', 'utilization': 0.85,
             'capacity': 1.0,  'cost_hr': 3.50, 'available': True},
            {'id': 'GPU-V100',  'type': 'GPU', 'utilization': 0.60,
             'capacity': 1.0,  'cost_hr': 2.10, 'available': True},
            {'id': 'CPU-Large', 'type': 'CPU', 'utilization': 0.40,
             'capacity': 1.0,  'cost_hr': 0.80, 'available': True},
            {'id': 'CPU-Small', 'type': 'CPU', 'utilization': 0.20,
             'capacity': 1.0,  'cost_hr': 0.30, 'available': True},
        ]
        print(f"[DRAA] Agent initialized with {len(self.resources)} resources")

    def scale_decision(self, utilization, capacity):
        if utilization > capacity * 0.80:
            return 'SCALE_UP'
        elif utilization < capacity * 0.30:
            return 'SCALE_DOWN'
        return 'HOLD'

    def allocate(self, latency_result):
        print(f"[DRAA] Allocating resources for job: {latency_result['job_id']}")

        allocations = []
        total_cost = 0
        scale_actions = []

        for a in latency_result['assignments']:
            # Find the matching resource
            resource = next(
                (r for r in self.resources if r['id'] == a['resource']),
                self.resources[-1]
            )

            # Scaling decision for this resource
            decision = self.scale_decision(
                resource['utilization'],
                resource['capacity']
            )

            if decision != 'HOLD':
                scale_actions.append({
                    'resource': resource['id'],
                    'action': decision,
                    'reason': f"utilization={resource['utilization']*100:.0f}%"
                })

            # Estimate cost (assume avg 5 min per task)
            task_cost = resource['cost_hr'] * (5 / 60)

            allocations.append({
                'task': a['task'],
                'resource': resource['id'],
                'resource_type': resource['type'],
                'utilization_pct': round(resource['utilization'] * 100, 1),
                'scale_decision': decision,
                'cost_usd': round(task_cost, 4),
                'scheduled_time': a['scheduled_time'],
                'sla_status': a['sla_status'],
                'carbon_gco2': a['carbon_gco2'],
                'latency_ms': a['latency_ms']
            })
            total_cost += task_cost

        avg_utilization = sum(
            r['utilization'] for r in self.resources
        ) / len(self.resources)

        result = {
            'job_id': latency_result['job_id'],
            'agent': self.name,
            'allocations': allocations,
            'total_cost_usd': round(total_cost, 4),
            'avg_utilization_pct': round(avg_utilization * 100, 1),
            'scale_actions': scale_actions,
            'sla_compliance_pct': latency_result['sla_compliance_pct'],
            'status': 'ALLOCATED'
        }

        print(f"[DRAA] Total cost: ${round(total_cost, 4)}")
        print(f"[DRAA] Avg utilization: {round(avg_utilization*100, 1)}%")
        print(f"[DRAA] Scale actions: {len(scale_actions)}")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    # Simulated output from LMA (Agent 4)
    latency_result = {
        'job_id': 'JOB-001',
        'sla_compliance_pct': 100.0,
        'assignments': [
            {'task': 'preprocess_data', 'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'sla_status': 'SAFE',
             'carbon_gco2': 0.1778, 'latency_ms': 13800},
            {'task': 'train_model',     'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'sla_status': 'SAFE',
             'carbon_gco2': 0.7999, 'latency_ms': 13800},
            {'task': 'validate_model',  'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'sla_status': 'SAFE',
             'carbon_gco2': 0.2666, 'latency_ms': 13800},
            {'task': 'generate_report', 'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'sla_status': 'SAFE',
             'carbon_gco2': 0.0888, 'latency_ms': 13800},
        ]
    }

    agent = DynamicResourceAllocationAgent.remote()
    result = ray.get(agent.allocate.remote(latency_result))

    print("\n" + "="*50)
    print("RESOURCE ALLOCATION AGENT — RESULTS")
    print("="*50)
    print(f"Job ID          : {result['job_id']}")
    print(f"Total Cost      : ${result['total_cost_usd']}")
    print(f"Avg Utilization : {result['avg_utilization_pct']}%")
    print(f"SLA Compliance  : {result['sla_compliance_pct']}%")
    print(f"Status          : {result['status']}")

    if result['scale_actions']:
        print(f"\nScale actions needed:")
        for s in result['scale_actions']:
            print(f"  ⚡ {s['resource']} → {s['action']} ({s['reason']})")
    else:
        print(f"\nNo scaling actions needed")

    print("\nFinal allocations:")
    for a in result['allocations']:
        print(f"  {a['task']:<20} → {a['resource']:<12} "
              f"| {a['utilization_pct']}% util "
              f"| ${a['cost_usd']} "
              f"| {a['sla_status']}")

    ray.shutdown()