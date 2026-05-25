from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import json
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'macsea2026'
socketio = SocketIO(app, cors_allowed_origins="*")


def run_macsea_live(n_jobs=10):
    """Run MACSEA on real data and emit live updates."""
    import ray
    from agents.wpa  import WorkflowPlanningAgent
    from agents.eoa  import EnergyOptimizationAgent
    from agents.cera import CarbonReductionAgent
    from agents.lma  import LatencyManagementAgent
    from agents.draa import DynamicResourceAllocationAgent
    from data.historical_carbon import get_current_intensity

    ray.init(ignore_reinit_error=True)

    socketio.emit('log', {'type': 'info',
        'msg': '[RAY] Started Ray instance — agents launching...'})
    time.sleep(0.5)

    wpa  = WorkflowPlanningAgent.remote()
    eoa  = EnergyOptimizationAgent.remote()
    cera = CarbonReductionAgent.remote()
    lma  = LatencyManagementAgent.remote()
    draa = DynamicResourceAllocationAgent.remote()

    socketio.emit('log', {'type': 'success',
        'msg': '[MACSEA] All 5 Ray agents initialized'})

    # Get real carbon intensity
    carbon_now = get_current_intensity()
    socketio.emit('log', {'type': 'info',
        'msg': f"[CERA] Real carbon: {carbon_now['gco2_kwh']} gCO2/kWh "
               f"(IN-SO, {carbon_now['source']})"})

    # Load real workload
    with open('data/workload_100.json') as f:
        all_jobs = json.load(f)
    jobs = all_jobs[:n_jobs]

    socketio.emit('log', {'type': '',
        'msg': f'[COORDINATOR] Scheduling {len(jobs)} real jobs...'})

    results = []
    start_total = time.time()

    for i, job in enumerate(jobs):
        start = time.time()

        socketio.emit('log', {'type': '',
            'msg': f"[WPA] Planning {job['id']} — {job['type']}"})

        wpa_r  = ray.get(wpa.plan.remote(job))
        eoa_r  = ray.get(eoa.optimize.remote(wpa_r))
        cera_r = ray.get(cera.schedule.remote(eoa_r))
        lma_r  = ray.get(lma.check_and_schedule.remote(cera_r))
        draa_r = ray.get(draa.allocate.remote(lma_r))

        elapsed = round(time.time() - start, 3)

        result = {
            'job_id':          job['id'],
            'job_type':        job['type'],
            'priority':        job['priority'],
            'n_tasks':         len(job['tasks']),
            'energy_wh':       round(eoa_r['total_energy_kwh'] * 1000, 4),
            'carbon_gco2':     cera_r['total_carbon_gco2'],
            'carbon_saved':    cera_r['savings_percent'],
            'best_slot':       cera_r['best_time_slot'],
            'sla':             lma_r['sla_compliance_pct'],
            'cost':            draa_r['total_cost_usd'],
            'utilization':     draa_r['avg_utilization_pct'],
            'schedule_time':   elapsed,
            'data_source':     'EMBER_Historical_IN-SO_2024',
        }
        results.append(result)

        socketio.emit('log', {'type': 'success',
            'msg': f"[DONE] {job['id']} | "
                   f"Energy: {result['energy_wh']}Wh | "
                   f"Carbon: {result['carbon_gco2']}gCO2 | "
                   f"Slot: {result['best_slot']} | "
                   f"SLA: {result['sla']}%"})

        socketio.emit('job_result', {
            'result': result,
            'progress': round((i + 1) / len(jobs) * 100),
            'job_num': i + 1,
            'total': len(jobs)
        })

        time.sleep(0.3)

    total_time = round(time.time() - start_total, 2)

    # Summary stats
    summary = {
        'total_jobs':      len(results),
        'total_time':      total_time,
        'avg_energy':      round(sum(r['energy_wh'] for r in results)
                                 / len(results), 4),
        'avg_carbon':      round(sum(r['carbon_gco2'] for r in results)
                                 / len(results), 4),
        'avg_carbon_saved':round(sum(r['carbon_saved'] for r in results)
                                 / len(results), 1),
        'avg_sla':         round(sum(r['sla'] for r in results)
                                 / len(results), 1),
        'avg_cost':        round(sum(r['cost'] for r in results)
                                 / len(results), 4),
        'avg_util':        round(sum(r['utilization'] for r in results)
                                 / len(results), 1),
        'results':         results,
        'carbon_source':   'EMBER_Historical_IN-SO_2024',
        'workload_source': 'Google_Cluster_Trace_2011',
    }

    socketio.emit('experiment_done', summary)
    socketio.emit('log', {'type': 'success',
        'msg': f'[MACSEA] Complete! {len(results)} jobs in {total_time}s'})

    ray.shutdown()


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/baselines')
def baselines():
    """Return real baseline results."""
    import pandas as pd
    try:
        rr  = pd.read_csv('results/round_robin_results.csv')
        heft= pd.read_csv('results/heft_results.csv')
        mm  = pd.read_csv('results/min_min_results.csv')
        mac = pd.read_csv('results/macsea_results.csv')

        return jsonify({
            'labels': ['Round Robin', 'HEFT', 'Min-Min', 'MACSEA'],
            'energy': [
                round(rr['energy_wh'].mean(), 2),
                round(heft['energy_wh'].mean(), 2),
                round(mm['energy_wh'].mean(), 2),
                round(mac['energy_wh'].mean(), 2),
            ],
            'carbon': [
                round(rr['carbon_gco2'].mean(), 2),
                round(heft['carbon_gco2'].mean(), 2),
                round(mm['carbon_gco2'].mean(), 2),
                round(mac['carbon_gco2'].mean(), 2),
            ],
            'sla': [
                round(rr['sla_compliance'].mean(), 1),
                round(heft['sla_compliance'].mean(), 1),
                round(mm['sla_compliance'].mean(), 1),
                round(mac['sla_compliance'].mean(), 1),
            ],
            'cost': [
                round(rr['total_cost_usd'].mean(), 4),
                round(heft['total_cost_usd'].mean(), 4),
                round(mm['total_cost_usd'].mean(), 4),
                round(mac['total_cost_usd'].mean(), 4),
            ],
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/carbon_forecast')
def carbon_forecast():
    """Return real EMBER carbon forecast."""
    from data.historical_carbon import get_24h_forecast
    from datetime import datetime
    forecast = get_24h_forecast(datetime.now().month)
    return jsonify(forecast)


@socketio.on('start_experiment')
def handle_start(data):
    n_jobs = data.get('n_jobs', 10)
    thread = threading.Thread(
        target=run_macsea_live, args=(n_jobs,))
    thread.daemon = True
    thread.start()


if __name__ == '__main__':
    print("\n" + "="*50)
    print("MACSEA Dashboard starting...")
    print("Open browser at: http://localhost:5000")
    print("="*50 + "\n")
    socketio.run(app, debug=False, port=5000)