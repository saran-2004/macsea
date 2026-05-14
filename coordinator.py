import ray
import time

# Import all 5 agents
from agents.wpa  import WorkflowPlanningAgent
from agents.eoa  import EnergyOptimizationAgent
from agents.cera import CarbonReductionAgent
from agents.lma  import LatencyManagementAgent
from agents.draa import DynamicResourceAllocationAgent


def run_macsea(job):
    print("\n" + "="*60)
    print("MACSEA — MULTI-AGENT COORDINATOR STARTING")
    print("="*60)
    print(f"Job ID   : {job['id']}")
    print(f"Tasks    : {len(job['tasks'])}")
    print(f"Deadline : {job['deadline']} minutes")
    print("="*60)

    # ── Launch all 5 agents simultaneously ──
    print("\n[COORDINATOR] Launching all 5 agents...")
    wpa  = WorkflowPlanningAgent.remote()
    eoa  = EnergyOptimizationAgent.remote()
    cera = CarbonReductionAgent.remote()
    lma  = LatencyManagementAgent.remote()
    draa = DynamicResourceAllocationAgent.remote()

    # ── Pipeline: each agent feeds the next ──
    start_time = time.time()

    print("\n[COORDINATOR] Step 1/5 — Workflow Planning...")
    wpa_result = ray.get(wpa.plan.remote(job))

    print("\n[COORDINATOR] Step 2/5 — Energy Optimization...")
    eoa_result = ray.get(eoa.optimize.remote(wpa_result))

    print("\n[COORDINATOR] Step 3/5 — Carbon Reduction...")
    cera_result = ray.get(cera.schedule.remote(eoa_result))

    print("\n[COORDINATOR] Step 4/5 — Latency Management...")
    lma_result = ray.get(lma.check_and_schedule.remote(cera_result))

    print("\n[COORDINATOR] Step 5/5 — Resource Allocation...")
    draa_result = ray.get(draa.allocate.remote(lma_result))

    elapsed = round(time.time() - start_time, 2)

    # ── Final MACSEA Report ──
    print("\n" + "="*60)
    print("MACSEA — FINAL SCHEDULING REPORT")
    print("="*60)
    print(f"Job ID           : {job['id']}")
    print(f"Scheduling Time  : {elapsed}s")
    print(f"Tasks Planned    : {wpa_result['total_tasks']}")
    print(f"Critical Task    : {wpa_result['critical_task']}")
    print(f"Total Energy     : {eoa_result['total_energy_kwh']*1000:.4f} Wh")
    print(f"Carbon Saved     : {cera_result['savings_percent']}%")
    print(f"Best Time Slot   : {cera_result['best_time_slot']}")
    print(f"Total Carbon     : {cera_result['total_carbon_gco2']} gCO2")
    print(f"SLA Compliance   : {lma_result['sla_compliance_pct']}%")
    print(f"Escalation       : {lma_result['escalation']}")
    print(f"Total Cost       : ${draa_result['total_cost_usd']}")
    print(f"Avg Utilization  : {draa_result['avg_utilization_pct']}%")
    print(f"Scale Actions    : {len(draa_result['scale_actions'])}")

    print("\n── Final Task Schedule ──")
    print(f"{'Task':<22} {'Resource':<12} {'Time':<8} "
          f"{'Carbon':>10} {'Latency':>10} {'SLA':>8} {'Cost':>8}")
    print("-"*80)
    for a in draa_result['allocations']:
        print(f"{a['task']:<22} {a['resource']:<12} "
              f"{a['scheduled_time']:<8} "
              f"{str(a['carbon_gco2'])+'gCO2':>10} "
              f"{str(a['latency_ms'])+'ms':>10} "
              f"{a['sla_status']:>8} "
              f"${a['cost_usd']:>6}")

    print("\n" + "="*60)
    print("MACSEA SCHEDULING COMPLETE")
    print("="*60)

    return draa_result


# ── Run MACSEA ────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    # Define a job
    job = {
        'id': 'JOB-001',
        'deadline': 60,
        'tasks': [
            {'name': 'preprocess_data',  'priority': 1, 'duration': 10},
            {'name': 'train_model',      'priority': 2, 'duration': 45},
            {'name': 'validate_model',   'priority': 3, 'duration': 15},
            {'name': 'generate_report',  'priority': 4, 'duration': 5},
        ]
    }

    result = run_macsea(job)
    ray.shutdown()