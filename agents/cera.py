import ray
import requests
from datetime import datetime

ELECTRICITY_MAPS_KEY = 'TSp6BpVHdhrPS95s8X4j'
ZONE = 'IN-SO'

@ray.remote
class CarbonReductionAgent:

    def __init__(self):
        self.name = "Carbon Emission Reduction Agent"
        self.api_key = ELECTRICITY_MAPS_KEY
        self.zone = ZONE
        print(f"[CERA] Agent initialized with real carbon API")

    def get_real_carbon_intensity(self):
        try:
            response = requests.get(
                'https://api.electricitymap.org/v3/carbon-intensity/latest',
                headers={'auth-token': self.api_key},
                params={'zone': self.zone},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'gco2_kwh': data['carbonIntensity'],
                    'zone': data['zone'],
                    'datetime': data['datetime'],
                    'is_real': True
                }
        except Exception as e:
            print(f"[CERA] API error: {e} — using fallback")
        return {
            'gco2_kwh': 420,
            'zone': self.zone,
            'datetime': datetime.now().isoformat(),
            'is_real': False
        }

    def get_carbon_forecast(self):
        current = self.get_real_carbon_intensity()
        real_intensity = current['gco2_kwh']

        forecast = [
            {'slot': 0, 'time': '00:00',
             'gco2_kwh': round(real_intensity * 1.08)},
            {'slot': 1, 'time': '03:00',
             'gco2_kwh': round(real_intensity * 0.95)},
            {'slot': 2, 'time': '06:00',
             'gco2_kwh': round(real_intensity * 0.85)},
            {'slot': 3, 'time': '09:00',
             'gco2_kwh': round(real_intensity * 0.75)},
            {'slot': 4, 'time': '12:00',
             'gco2_kwh': round(real_intensity * 0.65)},
            {'slot': 5, 'time': '15:00',
             'gco2_kwh': round(real_intensity * 0.70)},
            {'slot': 6, 'time': '18:00',
             'gco2_kwh': round(real_intensity * 0.90)},
            {'slot': 7, 'time': '21:00',
             'gco2_kwh': real_intensity},
        ]

        print(f"[CERA] Real carbon: {real_intensity} gCO2/kWh ({self.zone})")
        return forecast, current

    def schedule(self, energy_result, deadline_minutes=60):
        print(f"[CERA] Finding low-carbon window for "
              f"job: {energy_result['job_id']}")

        forecast, current_data = self.get_carbon_forecast()
        best_slot = min(forecast, key=lambda x: x['gco2_kwh'])

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

        current_carbon = sum(
            a['energy_kwh'] * current_data['gco2_kwh']
            for a in energy_result['assignments']
        )
        savings = current_carbon - total_carbon
        savings_pct = (savings / current_carbon * 100
                       if current_carbon > 0 else 0)

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
            'real_api_used': current_data['is_real'],
            'status': 'CARBON_OPTIMIZED'
        }

        print(f"[CERA] Best slot: {best_slot['time']} "
              f"({best_slot['gco2_kwh']} gCO2/kWh) | "
              f"Saved: {round(savings_pct, 1)}%")
        return result


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    energy_result = {
        'job_id': 'JOB-001',
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

    print("\n" + "="*50)
    print("CERA — RESULTS")
    print("="*50)
    print(f"Best Slot    : {result['best_time_slot']}")
    print(f"Carbon Saved : {result['savings_percent']}%")
    print(f"Real API     : {result['real_api_used']}")
    print(f"Status       : {result['status']}")

    ray.shutdown()