import psutil
from pynvml import *

# CPU Usage
cpu_percent = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()

print("CPU Usage:", cpu_percent, "%")
print("Memory Usage:", memory.percent, "%")

# GPU Monitoring
try:
    nvmlInit()

    device_count = nvmlDeviceGetCount()
    print("\nGPU Count:", device_count)

    for i in range(device_count):
        handle = nvmlDeviceGetHandleByIndex(i)

        name = nvmlDeviceGetName(handle)
        power = nvmlDeviceGetPowerUsage(handle) / 1000  # watts
        utilization = nvmlDeviceGetUtilizationRates(handle)

        print(f"\nGPU {i}:")
        print("Name:", name)
        print("Power Usage:", power, "W")
        print("GPU Utilization:", utilization.gpu, "%")
        print("Memory Utilization:", utilization.memory, "%")

    nvmlShutdown()

except Exception as e:
    print("\nGPU Monitoring Error:")
    print(e)