import pandas as pd
import gzip
import json
import random

# Google Cluster Trace 2011 column names
COLUMNS = [
    'timestamp', 'missing_info', 'job_id', 'task_index',
    'machine_id', 'event_type', 'user_name', 'scheduling_class',
    'priority', 'cpu_request', 'memory_request',
    'disk_request', 'different_machines'
]

# Event types
EVENT_TYPES = {
    0: 'SUBMIT',
    1: 'SCHEDULE',
    2: 'EVICT',
    3: 'FAIL',
    4: 'FINISH',
    5: 'KILL',
    6: 'LOST',
    7: 'UPDATE_PENDING',
    8: 'UPDATE_RUNNING'
}

# Priority classes mapping
PRIORITY_MAP = {
    0: 'BACKGROUND',
    1: 'BACKGROUND',
    2: 'BACKGROUND',
    3: 'BACKGROUND',
    4: 'NORMAL',
    5: 'NORMAL',
    6: 'HIGH',
    7: 'HIGH',
    8: 'CRITICAL',
    9: 'CRITICAL',
    10: 'CRITICAL',
    11: 'CRITICAL',
}

# Job type mapping
JOB_TYPE_MAP = {
    0: 'batch_prediction',
    1: 'data_preprocessing',
    2: 'model_training',
    3: 'llm_inference',
}


def load_google_trace(
    filepath='data/google_trace/task_events.csv.gz',
    n_jobs=100
):
    """
    Load Google Cluster Trace data and convert
    to MACSEA-compatible workload format.
    """

    print(f"Loading Google Cluster Trace from {filepath}...")

    # Read compressed CSV
    with gzip.open(filepath, 'rt') as f:
        df = pd.read_csv(
            f,
            header=None,
            names=COLUMNS,
            on_bad_lines='skip'
        )

    print(f"Raw records loaded: {len(df)}")

    # Keep only SUBMIT events
    submitted = df[df['event_type'] == 0].copy()

    print(f"Submitted tasks: {len(submitted)}")

    # Remove missing job IDs
    submitted = submitted.dropna(subset=['job_id'])

    submitted['job_id'] = submitted['job_id'].astype(int)

    # Group by job
    job_groups = submitted.groupby('job_id')

    print(f"Unique jobs found: {len(job_groups)}")

    macsea_jobs = []

    job_count = 0

    for job_id, group in job_groups:

        if job_count >= n_jobs:
            break

        tasks = []

        for _, row in group.iterrows():

            cpu_req = (
                float(row['cpu_request'])
                if pd.notna(row['cpu_request'])
                else 0.1
            )

            mem_req = (
                float(row['memory_request'])
                if pd.notna(row['memory_request'])
                else 0.1
            )

            # Estimate duration
            duration = max(
                5,
                min(300, cpu_req * 200 + 10)
            )

            task_index = (
                int(row['task_index'])
                if pd.notna(row['task_index'])
                else 0
            )

            tasks.append({
                'name': f"task_{task_index}",
                'priority': task_index,
                'duration': round(duration, 1),
                'cpu_request': round(cpu_req, 4),
                'memory_request': round(mem_req, 4),
            })

        if not tasks:
            continue

        # Job priority
        raw_priority = (
            int(group['priority'].iloc[0])
            if pd.notna(group['priority'].iloc[0])
            else 0
        )

        priority_class = PRIORITY_MAP.get(
            min(raw_priority, 11),
            'NORMAL'
        )

        # Scheduling class
        sched_class = (
            int(group['scheduling_class'].iloc[0])
            if pd.notna(group['scheduling_class'].iloc[0])
            else 0
        )

        job_type = JOB_TYPE_MAP.get(
            sched_class % 4,
            'batch_prediction'
        )

        # Deadline ranges
        deadline_ranges = {
            'CRITICAL': (10, 30),
            'HIGH': (30, 90),
            'NORMAL': (60, 180),
            'BACKGROUND': (120, 480),
        }

        dl_range = deadline_ranges[priority_class]

        deadline = random.randint(*dl_range)

        macsea_jobs.append({
            'id': f"GCT-{job_id}",
            'type': job_type,
            'priority': priority_class,
            'deadline': deadline,
            'tasks': tasks[:5],
            'source': 'Google_Cluster_Trace_2011',
            'original_job_id': int(job_id),
            'data_size_gb': round(
                sum(
                    t['memory_request']
                    for t in tasks
                ) * 10,
                2
            ),
        })

        job_count += 1

    print(f"Converted {len(macsea_jobs)} real Google jobs!")

    return macsea_jobs


def print_summary(jobs):

    print("\n" + "=" * 55)
    print("GOOGLE CLUSTER TRACE — WORKLOAD SUMMARY")
    print("Source: Google Cluster Trace 2011 (Real Data)")
    print("=" * 55)

    print(f"Total Jobs     : {len(jobs)}")
    print(f"Data Source    : {jobs[0]['source']}")

    # Job type counts
    type_counts = {}

    for job in jobs:
        type_counts[job['type']] = (
            type_counts.get(job['type'], 0) + 1
        )

    print("\nBy job type:")

    for jtype, count in sorted(
        type_counts.items(),
        key=lambda x: -x[1]
    ):
        bar = "█" * count
        print(f"  {jtype:<25} {count:>3} {bar}")

    # Priority counts
    priority_counts = {}

    for job in jobs:
        priority_counts[job['priority']] = (
            priority_counts.get(job['priority'], 0) + 1
        )

    print("\nBy priority:")

    for p in ['CRITICAL', 'HIGH', 'NORMAL', 'BACKGROUND']:
        count = priority_counts.get(p, 0)
        bar = "█" * count
        print(f"  {p:<12} {count:>3} {bar}")

    total_tasks = sum(len(j['tasks']) for j in jobs)

    avg_tasks = total_tasks / len(jobs)

    avg_deadline = (
        sum(j['deadline'] for j in jobs) / len(jobs)
    )

    print(f"\nTotal tasks    : {total_tasks}")
    print(f"Avg tasks/job  : {round(avg_tasks, 1)}")
    print(f"Avg deadline   : {round(avg_deadline, 1)} minutes")

    print("=" * 55)

    # Sample jobs
    print("\nSample real Google jobs:")

    for job in jobs[:3]:

        print(
            f"\n  [{job['id']}] "
            f"{job['type']} | "
            f"Priority: {job['priority']} | "
            f"Deadline: {job['deadline']}min | "
            f"Tasks: {len(job['tasks'])}"
        )

        for t in job['tasks']:

            print(
                f"    → {t['name']:<15} "
                f"CPU: {t['cpu_request']} | "
                f"Mem: {t['memory_request']} | "
                f"Duration: {t['duration']}s"
            )


if __name__ == "__main__":

    jobs = load_google_trace(n_jobs=100)

    if jobs:

        print_summary(jobs)

        # Save workload
        with open(
            'data/google_trace_workload.json',
            'w'
        ) as f:
            json.dump(jobs, f, indent=2)

        print("\nSaved to data/google_trace_workload.json")
        print("Ready to run MACSEA on real Google workload!")

    else:
        print("No jobs loaded — check the trace file!")