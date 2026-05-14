import ray
import random

@ray.remote
class WorkflowPlanningAgent:
    
    def __init__(self):
        self.name = "Workflow Planning Agent"
        print(f"[WPA] Agent initialized")

    def plan(self, job):
        print(f"[WPA] Planning job: {job['id']}")

        # Sort tasks by priority (lower number = higher priority)
        sorted_tasks = sorted(job['tasks'], key=lambda t: t['priority'])

        # Find critical path (longest chain)
        critical = sorted_tasks[0]['name']

        result = {
            'job_id': job['id'],
            'agent': self.name,
            'planned_tasks': sorted_tasks,
            'critical_task': critical,
            'total_tasks': len(sorted_tasks),
            'status': 'PLANNED'
        }

        print(f"[WPA] Done — {len(sorted_tasks)} tasks planned, critical: {critical}")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":

    # Start Ray
    ray.init(ignore_reinit_error=True)

    # Create a sample job
    sample_job = {
        'id': 'JOB-001',
        'deadline': 120,
        'tasks': [
            {'name': 'preprocess_data',  'priority': 1, 'duration': 10},
            {'name': 'train_model',      'priority': 2, 'duration': 45},
            {'name': 'validate_model',   'priority': 3, 'duration': 15},
            {'name': 'generate_report',  'priority': 4, 'duration': 5},
        ]
    }

    # Create and run the agent
    agent = WorkflowPlanningAgent.remote()
    result = ray.get(agent.plan.remote(sample_job))

    # Print results
    print("\n" + "="*50)
    print("WORKFLOW PLANNING AGENT — RESULTS")
    print("="*50)
    print(f"Job ID      : {result['job_id']}")
    print(f"Total Tasks : {result['total_tasks']}")
    print(f"Critical    : {result['critical_task']}")
    print(f"Status      : {result['status']}")
    print("\nPlanned order:")
    for i, task in enumerate(result['planned_tasks'], 1):
        print(f"  {i}. {task['name']} (priority={task['priority']}, duration={task['duration']}s)")
    input("Press Enter to stop Ray...")
    ray.shutdown()
    