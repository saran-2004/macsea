import ray
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.historical_carbon import get_24h_forecast, get_current_intensity
from datetime import datetime

@ray.remote
class CarbonReductionAgent:

    def __init__(self):
        self.name = "Carbon Emission Reduction Agent"
        self.zone = "IN-SO"
        self.data_source = "EMBER_Historical_IN-SO_2024"
        print(f"[CERA] Agent initialized with "
              f"EMBER historical carbon data")

    def get_carbon_forecast(self):
        """Get 24h forecast from real EMBER historical data."""
        now = datetime.now()
        forecast = get_24h_forecast(now.month)
        current = get_current_intensity(now.month, now.hour)
        print(f"[CERA] Historical carbon: "
              f"{current['gco2_kwh']} gCO2/kWh "
              f"({now.strftime('%B')}, Hour {now.hour})")
        return forecast, current

    def schedule(self, energy_result, deadline_minutes=60):
        print(f"[CERA] Finding low-carbon window for "
              f"job: {energy_result['job_id']}")

        forecast, current_data = self.get_carbon_forecast()

        # Find best slot within deadline
        current_hour = datetime.now().hour
        deadline_hours = deadline_minutes // 60 or 1

        # Filter slots within deadline window
        eligible = [
            s for s in forecast
            if current_hour <= s['hour'] <=
            min(current_hour + deadline_hours + 6, 23)
        ] or forecast  # fallback to all slots

        best_slot = min(eligible, key=lambda x: x['gco2_kwh'])
        worst_slot = max(forecast, key=lambda x: x['gco2_kwh'])

        assignments = []
        total_carbon = 0

        for a in energy_result['assignments']:
            carbon_g = a['energy_kwh'] * best_slot['gco2_kwh']
            assignments.append({
                'task':             a['task'],
                'resource':         a['resource'],
                'scheduled_time':   best_slot['time'],
                'carbon_intensity': best_slot['gco2_kwh'],
                'energy_kwh':       a['energy_kwh'],
                'carbon_gco2':      round(carbon_g, 4),
                'data_source':      self.data_source,
            })
            total_carbon += carbon_g

        # Carbon if run now vs optimal slot
        current_carbon = sum(
            a['energy_kwh'] * current_data['gco2_kwh']
            for a in energy_result['assignments']
        )
        # Max possible savings vs worst slot
        worst_carbon = sum(
            a['energy_kwh'] * worst_slot['gco2_kwh']
            for a in energy_result['assignments']
        )

        savings = current_carbon - total_carbon
        savings_pct = (savings / current_carbon * 100
                       if current_carbon > 0 else 0)
        max_savings_pct = ((worst_carbon - total_carbon)
                           / worst_carbon * 100
                           if worst_carbon > 0 else 0)

        result = {
            'job_id':            energy_result['job_id'],
            'agent':             self.name,
            'assignments':       assignments,
            'best_time_slot':    best_slot['time'],
            'carbon_intensity':  best_slot['gco2_kwh'],
            'total_carbon_gco2': round(total_carbon, 4),
            'carbon_if_now':     round(current_carbon, 4),
            'carbon_saved_gco2': round(savings, 4),
            'savings_percent':   round(savings_pct, 1),
            'max_savings_pct':   round(max_savings_pct, 1),
            'data_source':       self.data_source,
            'zone':              self.zone,
            'status':            'CARBON_OPTIMIZED'
        }

        print(f"[CERA] Best: {best_slot['time']} "
              f"({best_slot['gco2_kwh']} gCO2/kWh) | "
              f"Saved: {round(savings_pct, 1)}% | "
              f"Source: EMBER Historical")
        return result


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    energy_result = {
        'job_id': 'JOB-TEST',
        'assignments': [
            {'task': 'preprocess_data', 'resource': 'CPU-Small',
             'energy_kwh': 0.000741},
            {'task': 'train_model', 'resource': 'CPU-Small',
             'energy_kwh': 0.003333},
            {'task': 'validate_model', 'resource': 'CPU-Small',
             'energy_kwh': 0.001111},
            {'task': 'generate_report', 'resource': 'CPU-Small',
             'energy_kwh': 0.000370},
        ]
    }

    agent = CarbonReductionAgent.remote()
    result = ray.get(agent.schedule.remote(energy_result))

    print("\n" + "="*55)
    print("CERA — EMBER HISTORICAL CARBON DATA")
    print("="*55)
    print(f"Job ID         : {result['job_id']}")
    print(f"Best Slot      : {result['best_time_slot']}")
    print(f"Carbon Saved   : {result['savings_percent']}%")
    print(f"Max Possible   : {result['max_savings_pct']}%")
    print(f"Data Source    : {result['data_source']}")
    print(f"Zone           : {result['zone']}")
    print(f"Status         : {result['status']}")
    print("\nTask schedule:")
    for a in result['assignments']:
        print(f"  {a['task']:<20} → {a['scheduled_time']} "
              f"| {a['carbon_intensity']} gCO2/kWh "
              f"| {a['carbon_gco2']} gCO2")

    ray.shutdown()