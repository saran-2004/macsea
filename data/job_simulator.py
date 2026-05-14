import random
import uuid
from datetime import datetime, timedelta

# Realistic AI job types based on Google Cluster Trace patterns
JOB_TYPES = [
    'llm_inference',
    'model_training',
    'data_preprocessing',
    'batch_prediction',
    'model_validation',
    'feature_engineering',
    'hyperparameter_tuning',
    'model_serving',
]

TASK_TEMPLATES = {
    'llm_inference': [
        {'name': 'tokenize_input',     'priority': 1, 'duration': 2},
        {'name': 'run_inference',      'priority': 2, 'duration': 15},
        {'name': 'postprocess_output', 'priority': 3, 'duration': 3},
    ],
    'model_training': [
        {'name': 'load_dataset',       'priority': 1, 'duration': 20},
        {'name': 'preprocess_data',    'priority': 2, 'duration': 30},
        {'name': 'train_model',        'priority': 3, 'duration': 120},
        {'name': 'evaluate_model',     'priority': 4, 'duration': 15},
        {'name': 'save_checkpoint',    'priority': 5, 'duration': 5},
    ],
    'data_preprocessing': [
        {'name': 'ingest_raw_data',    'priority': 1, 'duration': 10},
        {'name': 'clean_data',         'priority': 2, 'duration': 25},
        {'name': 'transform_features', 'priority': 3, 'duration': 20},
        {'name': 'validate_output',    'priority': 4, 'duration': 8},
    ],
    'batch_prediction': [
        {'name': 'load_model',         'priority': 1, 'duration': 5},
        {'name': 'load_batch',         'priority': 2, 'duration': 10},
        {'name': 'run_predictions',    'priority': 3, 'duration': 40},
        {'name': 'store_results',      'priority': 4, 'duration': 6},
    ],
    'model_validation': [
        {'name': 'load_test_data',     'priority': 1, 'duration': 8},
        {'name': 'run_validation',     'priority': 2, 'duration': 25},
        {'name': 'compute_metrics',    'priority': 3, 'duration': 10},
        {'name': 'generate_report',    'priority': 4, 'duration': 5},
    ],
    'feature_engineering': [
        {'name': 'extract_features',   'priority': 1, 'duration': 35},
        {'name': 'select_features',    'priority': 2, 'duration': 20},
        {'name': 'store_features',     'priority': 3, 'duration': 8},
    ],
    'hyperparameter_tuning': [
        {'name': 'define_search_space','priority': 1, 'duration': 3},
        {'name': 'run_trials',         'priority': 2, 'duration': 180},
        {'name': 'select_best_params', 'priority': 3, 'duration': 5},
        {'name': 'retrain_best_model', 'priority': 4, 'duration': 90},
    ],
    'model_serving': [
        {'name': 'load_model',         'priority': 1, 'duration': 4},
        {'name': 'warm_up_cache',      'priority': 2, 'duration': 6},
        {'name': 'start_server',       'priority': 3, 'duration': 3},
        {'name': 'health_check',       'priority': 4, 'duration': 2},
    ],
}

PRIORITY_CLASSES = ['CRITICAL', 'HIGH', 'NORMAL', 'BACKGROUND']
DEADLINE_RANGES = {
    'CRITICAL':   (10,  30),
    'HIGH':       (30,  90),
    'NORMAL':     (60,  180),
    'BACKGROUND': (120, 480),
}


def generate_job(job_id=None):
    """Generate a single realistic AI job."""
    job_type = random.choice(JOB_TYPES)
    priority = random.choice(PRIORITY_CLASSES)
    deadline_range = DEADLINE_RANGES[priority]

    # Add randomness to task durations (±30%)
    base_tasks = TASK_TEMPLATES[job_type]
    tasks = []
    for t in base_tasks:
        variation = random.uniform(0.7, 1.3)
        tasks.append({
            'name': t['name'],
            'priority': t['priority'],
            'duration': round(t['duration'] * variation, 1)
        })

    return {
        'id': job_id or f"JOB-{str(uuid.uuid4())[:8].upper()}",
        'type': job_type,
        'priority': priority,
        'deadline': random.randint(*deadline_range),
        'tasks': tasks,
        'submitted_at': datetime.now().isoformat(),
        'data_size_gb': round(random.uniform(0.1, 50.0), 2),
    }


def generate_workload(n_jobs=100, seed=42):
    """Generate a full workload of n jobs."""
    random.seed(seed)
    jobs = [generate_job(f"JOB-{i+1:04d}") for i in range(n_jobs)]
    return jobs


def print_workload_summary(jobs):
    """Print a summary of generated jobs."""
    print("\n" + "="*55)
    print("MACSEA — JOB WORKLOAD SUMMARY")
    print("="*55)
    print(f"Total Jobs     : {len(jobs)}")

    # Count by type
    type_counts = {}
    for job in jobs:
        type_counts[job['type']] = type_counts.get(job['type'], 0) + 1

    print("\nBy job type:")
    for jtype, count in sorted(type_counts.items(),
                                key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {jtype:<25} {count:>3} {bar}")

    # Count by priority
    priority_counts = {}
    for job in jobs:
        priority_counts[job['priority']] = \
            priority_counts.get(job['priority'], 0) + 1

    print("\nBy priority:")
    for p in PRIORITY_CLASSES:
        count = priority_counts.get(p, 0)
        bar = "█" * count
        print(f"  {p:<12} {count:>3} {bar}")

    # Stats
    all_tasks = sum(len(j['tasks']) for j in jobs)
    avg_deadline = sum(j['deadline'] for j in jobs) / len(jobs)
    avg_tasks = all_tasks / len(jobs)

    print(f"\nTotal tasks    : {all_tasks}")
    print(f"Avg tasks/job  : {round(avg_tasks, 1)}")
    print(f"Avg deadline   : {round(avg_deadline, 1)} minutes")
    print("="*55)

    # Show 3 sample jobs
    print("\nSample jobs:")
    for job in jobs[:3]:
        print(f"\n  [{job['id']}] {job['type']} | "
              f"Priority: {job['priority']} | "
              f"Deadline: {job['deadline']}min | "
              f"Data: {job['data_size_gb']}GB")
        for t in job['tasks']:
            print(f"    → {t['name']:<25} {t['duration']}s")


# ── Run it ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating 100 realistic AI jobs...")
    jobs = generate_workload(n_jobs=100)
    print_workload_summary(jobs)

    # Save to file for use by other modules
    import json
    with open('data/workload_100.json', 'w') as f:
        json.dump(jobs, f, indent=2)
    print(f"\nSaved to data/workload_100.json")