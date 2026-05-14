import ray
import time

@ray.remote
class LatencyManagementAgent:

    def __init__(self):
        self.name = "Latency Management Agent"
        print(f"[LMA] Agent initialized")

    def check_and_schedule(self, carbon_result, job_deadline_minutes=60):
        print(f"[LMA] Checking latency for job: {carbon_result['job_id']}")

        assignments = []
        total_latency = 0
        any_violation = False

        for a in carbon_result['assignments']:
            # Latency model: queue + execution + network
            l_queue   = 2.5        # avg queue wait (seconds)
            l_exec    = 10.0       # execution latency
            l_network = 0.8        # network transfer
            l_overhead = 0.5       # container startup
            total_task_latency = l_queue + l_exec + l_network + l_overhead

            # SLA budget per task (spread deadline evenly)
            sla_budget = (job_deadline_minutes * 60) / len(carbon_result['assignments'])
            slack = sla_budget - total_task_latency
            slack_pct = (slack / sla_budget) * 100

            # Determine status
            if slack_pct < 0:
                status = 'VIOLATED'
                any_violation = True
            elif slack_pct < 20:
                status = 'AT_RISK'
            else:
                status = 'SAFE'

            assignments.append({
                'task': a['task'],
                'resource': a['resource'],
                'scheduled_time': a['scheduled_time'],
                'latency_ms': round(total_task_latency * 1000),
                'sla_budget_s': round(sla_budget, 1),
                'slack_s': round(slack, 1),
                'slack_pct': round(slack_pct, 1),
                'sla_status': status,
                'carbon_gco2': a['carbon_gco2']
            })
            total_latency += total_task_latency

        sla_compliance = sum(
            1 for a in assignments if a['sla_status'] == 'SAFE'
        ) / len(assignments) * 100

        result = {
            'job_id': carbon_result['job_id'],
            'agent': self.name,
            'assignments': assignments,
            'total_latency_ms': round(total_latency * 1000),
            'sla_compliance_pct': round(sla_compliance, 1),
            'any_violation': any_violation,
            'escalation': 'REQUIRED' if any_violation else 'NONE',
            'status': 'LATENCY_CHECKED'
        }

        print(f"[LMA] SLA compliance: {sla_compliance}%")
        print(f"[LMA] Escalation: {result['escalation']}")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    # Simulated output from CERA (Agent 3)
    carbon_result = {
        'job_id': 'JOB-001',
        'assignments': [
            {'task': 'preprocess_data', 'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'carbon_gco2': 0.1778},
            {'task': 'train_model',     'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'carbon_gco2': 0.7999},
            {'task': 'validate_model',  'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'carbon_gco2': 0.2666},
            {'task': 'generate_report', 'resource': 'CPU-Small',
             'scheduled_time': '23:15', 'carbon_gco2': 0.0888},
        ]
    }

    agent = LatencyManagementAgent.remote()
    result = ray.get(agent.check_and_schedule.remote(carbon_result))

    print("\n" + "="*50)
    print("LATENCY MANAGEMENT AGENT — RESULTS")
    print("="*50)
    print(f"Job ID         : {result['job_id']}")
    print(f"Total Latency  : {result['total_latency_ms']} ms")
    print(f"SLA Compliance : {result['sla_compliance_pct']}%")
    print(f"Escalation     : {result['escalation']}")
    print(f"Status         : {result['status']}")
    print("\nTask SLA breakdown:")
    for a in result['assignments']:
        flag = "⚠" if a['sla_status'] == 'AT_RISK' else (
               "❌" if a['sla_status'] == 'VIOLATED' else "✓")
        print(f"  {flag} {a['task']:<20} | {a['latency_ms']}ms "
              f"| slack={a['slack_s']}s ({a['slack_pct']}%) "
              f"| {a['sla_status']}")

    ray.shutdown()