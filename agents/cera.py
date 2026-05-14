import ray
from datetime import datetime

@ray.remote
class CarbonReductionAgent:

    def __init__(self):
        self.name = "Carbon Emission Reduction Agent"
        print(f"[CERA] Agent initialized")

    def get_carbon_forecast(self):
        # Simulated carbon intensity forecast (gCO2eq/kWh)
        # In real system this comes from electricitymaps.com API
        return [
            {'slot': 0,  'time': '22:00', 'gco2_kwh': 420, 'region': 'IN-SO'},
            {'slot': 1,  'time': '22:15', 'gco2_kwh': 380, 'region': 'IN-SO'},
            {'slot': 2,  'time': '22:30', 'gco2_kwh': 310, 'region': 'IN-SO'},
            {'slot': 3,  'time': '22:45', 'gco2_kwh': 290, 'region': 'IN-SO'},
            {'slot': 4,  'time': '23:00', 'gco2_kwh': 260, 'region': 'IN-SO'},
            {'slot': 5,  'time': '23:15', 'gco2_kwh': 240, 'region': 'IN-SO'},
            {'slot': 6,  'time': '23:30', 'gco2_kwh': 280, 'region': 'IN-SO'},
            {'slot': 7,  'time': '23:45', 'gco2_kwh': 350, 'region': 'IN-SO'},
        ]

    def schedule(self, energy_result, deadline_minutes=60):
        print(f"[CERA] Finding low-carbon window for job: {energy_result['job_id']}")

        forecast = self.get_carbon_forecast()

        # Find the lowest carbon slot within deadline
        best_slot = min(forecast, key=lambda x: x['gco2_kwh'])

        # Calculate carbon emissions for each task
        assignments = []
        total_carbon = 0

        for a in energy_result['assignments']:
            carbon_g = a['energy_kwh'] * best_slot['gco2_kwh']
            assignments.append({
                'task': a['task'],
                'resource': a['resource'],
                'scheduled_time': best_slot['time'],
                'carbon_intensity': best_slot['gco2_kwh'],
                'energy_kwh': a['energy_kwh'],
                'carbon_gco2': round(carbon_g, 4)
            })
            total_carbon += carbon_g

        # Compare: what if we ran NOW vs optimal slot
        current_carbon = sum(
            a['energy_kwh'] * forecast[0]['gco2_kwh']
            for a in energy_result['assignments']
        )
        savings = current_carbon - total_carbon
        savings_pct = (savings / current_carbon) * 100

        result = {
            'job_id': energy_result['job_id'],
            'agent': self.name,
            'assignments': assignments,
            'best_time_slot': best_slot['time'],
            'carbon_intensity': best_slot['gco2_kwh'],
            'total_carbon_gco2': round(total_carbon, 4),
            'carbon_if_run_now': round(current_carbon, 4),
            'carbon_saved_gco2': round(savings, 4),
            'savings_percent': round(savings_pct, 1),
            'status': 'CARBON_OPTIMIZED'
        }

        print(f"[CERA] Best slot: {best_slot['time']} "
              f"({best_slot['gco2_kwh']} gCO2/kWh)")
        print(f"[CERA] Carbon saved: {round(savings*1000, 2)} mgCO2 "
              f"({round(savings_pct, 1)}% reduction)")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    # Simulated output from EOA (Agent 2)
    energy_result = {
        'job_id': 'JOB-001',
        'assignments': [
            {'task': 'preprocess_data', 'resource': 'CPU-Small',
             'energy_kwh': 0.000741},
            {'task': 'train_model',     'resource': 'CPU-Small',
             'energy_kwh': 0.003333},
            {'task': 'validate_model',  'resource': 'CPU-Small',
             'energy_kwh': 0.001111},
            {'task': 'generate_report', 'resource': 'CPU-Small',
             'energy_kwh': 0.000370},
        ]
    }

    agent = CarbonReductionAgent.remote()
    result = ray.get(agent.schedule.remote(energy_result))

    print("\n" + "="*50)
    print("CARBON REDUCTION AGENT — RESULTS")
    print("="*50)
    print(f"Job ID          : {result['job_id']}")
    print(f"Best Time Slot  : {result['best_time_slot']}")
    print(f"Carbon Intensity: {result['carbon_intensity']} gCO2/kWh")
    print(f"Total Carbon    : {result['total_carbon_gco2']} gCO2")
    print(f"Carbon if Now   : {result['carbon_if_run_now']} gCO2")
    print(f"Carbon Saved    : {result['carbon_saved_gco2']} gCO2 "
          f"({result['savings_percent']}% reduction)")
    print(f"Status          : {result['status']}")
    print("\nTask schedule:")
    for a in result['assignments']:
        print(f"  {a['task']:<20} → {a['scheduled_time']} "
              f"| {a['carbon_intensity']} gCO2/kWh "
              f"| {a['carbon_gco2']} gCO2")

    ray.shutdown()