import ray
import psutil
import time
from datetime import datetime

@ray.remote
class MonitoringAgent:

    def __init__(self):
        self.name = "Real-Time Monitoring Agent"
        self.start_time = time.time()
        print(f"[MONITOR] Agent initialized — watching system resources")

    def get_cpu_stats(self):
        """Real CPU usage from your machine."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'cpu_freq_mhz': round(psutil.cpu_freq().current, 1)
            if psutil.cpu_freq() else 0,
        }

    def get_memory_stats(self):
        """Real RAM usage from your machine."""
        mem = psutil.virtual_memory()
        return {
            'total_gb':     round(mem.total / 1e9, 2),
            'used_gb':      round(mem.used / 1e9, 2),
            'available_gb': round(mem.available / 1e9, 2),
            'percent_used': mem.percent,
        }

    def get_disk_stats(self):
        """Real disk usage."""
        disk = psutil.disk_usage('/')
        return {
            'total_gb': round(disk.total / 1e9, 2),
            'used_gb':  round(disk.used / 1e9, 2),
            'free_gb':  round(disk.free / 1e9, 2),
            'percent':  disk.percent,
        }

    def estimate_energy(self, cpu_percent, duration_s=1):
        """
        Estimate real energy consumption based on CPU usage.
        Uses TDP-based model (your CPU TDP ~ 15-45W for laptop)
        """
        # Laptop CPU TDP estimate
        cpu_tdp_watts = 35
        idle_watts = 8

        # Energy = idle + (TDP - idle) * utilization
        actual_watts = idle_watts + (cpu_tdp_watts - idle_watts) * (
            cpu_percent / 100)
        energy_wh = (actual_watts * duration_s) / 3600

        return {
            'estimated_watts': round(actual_watts, 2),
            'energy_wh': round(energy_wh, 6),
            'cpu_tdp_w': cpu_tdp_watts,
        }

    def snapshot(self):
        """Take a full system snapshot."""
        timestamp = datetime.now().isoformat()
        cpu   = self.get_cpu_stats()
        mem   = self.get_memory_stats()
        disk  = self.get_disk_stats()
        energy = self.estimate_energy(cpu['cpu_percent'])

        snapshot = {
            'timestamp':      timestamp,
            'cpu':            cpu,
            'memory':         mem,
            'disk':           disk,
            'energy':         energy,
            'uptime_s':       round(time.time() - self.start_time, 1),
        }

        print(f"[MONITOR] CPU: {cpu['cpu_percent']}% | "
              f"RAM: {mem['percent_used']}% | "
              f"Power: {energy['estimated_watts']}W")
        return snapshot

    def monitor_job(self, job_id, duration_s=3):
        """Monitor system during a job execution."""
        print(f"[MONITOR] Monitoring job {job_id} "
              f"for {duration_s} seconds...")
        snapshots = []
        for i in range(duration_s):
            snap = self.snapshot()
            snap['job_id'] = job_id
            snapshots.append(snap)
            time.sleep(1)

        # Compute averages
        avg_cpu    = sum(s['cpu']['cpu_percent']
                         for s in snapshots) / len(snapshots)
        avg_mem    = sum(s['memory']['percent_used']
                         for s in snapshots) / len(snapshots)
        total_energy = sum(s['energy']['energy_wh']
                           for s in snapshots)

        result = {
            'job_id':          job_id,
            'duration_s':      duration_s,
            'avg_cpu_pct':     round(avg_cpu, 1),
            'avg_memory_pct':  round(avg_mem, 1),
            'total_energy_wh': round(total_energy, 6),
            'avg_watts':       round(
                sum(s['energy']['estimated_watts']
                    for s in snapshots) / len(snapshots), 2),
            'snapshots':       len(snapshots),
            'source':          'psutil_real_measurement',
        }

        print(f"[MONITOR] Job {job_id} done — "
              f"Avg CPU: {avg_cpu:.1f}% | "
              f"Energy: {total_energy:.4f} Wh")
        return result


# ── Test it ──────────────────────────────────────────────
if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)

    monitor = MonitoringAgent.remote()

    print("\n" + "="*55)
    print("REAL-TIME MONITORING AGENT — LIVE SYSTEM DATA")
    print("="*55)

    # Single snapshot
    print("\n── Live System Snapshot ──")
    snap = ray.get(monitor.snapshot.remote())
    print(f"\nTimestamp     : {snap['timestamp']}")
    print(f"\nCPU")
    print(f"  Usage       : {snap['cpu']['cpu_percent']}%")
    print(f"  Cores       : {snap['cpu']['cpu_count']}")
    print(f"  Frequency   : {snap['cpu']['cpu_freq_mhz']} MHz")
    print(f"\nMemory")
    print(f"  Total       : {snap['memory']['total_gb']} GB")
    print(f"  Used        : {snap['memory']['used_gb']} GB")
    print(f"  Available   : {snap['memory']['available_gb']} GB")
    print(f"  Usage       : {snap['memory']['percent_used']}%")
    print(f"\nEnergy (estimated)")
    print(f"  Power       : {snap['energy']['estimated_watts']} W")
    print(f"  Energy      : {snap['energy']['energy_wh']} Wh")

    # Monitor a job for 3 seconds
    print(f"\n── Monitoring JOB-001 for 3 seconds ──")
    result = ray.get(monitor.monitor_job.remote('JOB-001', 3))
    print(f"\nJob ID        : {result['job_id']}")
    print(f"Duration      : {result['duration_s']}s")
    print(f"Avg CPU       : {result['avg_cpu_pct']}%")
    print(f"Avg Memory    : {result['avg_memory_pct']}%")
    print(f"Total Energy  : {result['total_energy_wh']} Wh")
    print(f"Avg Power     : {result['avg_watts']} W")
    print(f"Data Source   : {result['source']}")
    print("="*55)

    ray.shutdown()