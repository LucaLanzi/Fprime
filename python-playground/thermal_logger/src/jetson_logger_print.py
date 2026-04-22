import time
import datetime
import os
import sys
from pathlib import Path

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

# Import Jetson-specific configuration
from config_jetson import (
    JETSON_NUM_READINGS,
    JETSON_READ_INTERVAL, JETSON_CLIENT_DEVICE_ID,
    DEBUG, SIMULATE_SENSOR, TIMESTAMP_FORMAT, JETSON_THERMAL_ZONE_PATHS,
    MAX_THERMAL_ZONES, JETSON_SEND_EVERY, JETSON_SEND_FREQUENCY_HZ
)


# No local file logging and no remote server logging - data is printed to stdout

def read_jetson_thermal_zones():
    """
    Reads all available thermal zones from the Jetson system.

    Thermal zones are exposed by the Linux kernel at /sys/class/thermal/thermal_zoneX/temp
    Values are in millidegrees Celsius (divide by 1000 to get °C).

    Returns:
        dict: Thermal zone data organized by zone number
              Format: {
                  'zone_0': 45.2,
                  'zone_1': 42.1,
                  'zone_2': 38.5,
                  ...
              }
    """
    thermal_data = {}

    for zone_id, sensor_path in enumerate(JETSON_THERMAL_ZONE_PATHS):
        try:
            with open(sensor_path, 'r') as f:
                temp_millidegrees = int(f.read().strip())
                temp_celsius = temp_millidegrees / 1000.0
                thermal_data[f'zone_{zone_id}'] = round(temp_celsius, 2)
        except FileNotFoundError:
            continue
        except Exception as e:
            if DEBUG:
                print(f"Error reading thermal zone {zone_id} from {sensor_path}: {e}")
            continue

    if DEBUG and not thermal_data:
        print("Warning: Could not read any Jetson thermal zones. Check paths and permissions.")

    return thermal_data


def print_data_locally(thermal_data, sample_index, samples_read):
    """
    Prints Jetson thermal data locally instead of sending it over the network.

    Args:
        thermal_data: Dict with thermal zone data
        sample_index: Printed sample counter
        samples_read: Total read counter
    """
    timestamp = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)

    print(f"[PRINTED] [SAMPLE {sample_index}] [READ {samples_read}] [{timestamp}] "
          f"device_id:{JETSON_CLIENT_DEVICE_ID}", end="")
    for zone_id in range(MAX_THERMAL_ZONES):
        zone_key = f'zone_{zone_id}'
        if zone_key in thermal_data:
            print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
    print()


# Main program
try:
    print("[JETSON] *** LOCAL CONSOLE OUTPUT ONLY - No remote logging ***")

    if DEBUG:
        print(f"[JETSON] Taking {JETSON_NUM_READINGS} readings")
        print(f"[JETSON] Sampling: Reading every {JETSON_READ_INTERVAL}s, Printing every {JETSON_SEND_EVERY} sample(s)")

    if SIMULATE_SENSOR:
        print("[JETSON] *** SIMULATION MODE ENABLED ***")
        print("[JETSON] Using synthetic thermal sensor data for testing")

    print_interval = 1.0 / JETSON_SEND_FREQUENCY_HZ if JETSON_SEND_FREQUENCY_HZ > 0 else float('inf')
    last_print_time = time.time()

    samples_read = 0
    samples_printed = 0
    samples_since_print = 0

    start_real_time = time.time()
    sample_count = 0

    print(f"[JETSON] Print frequency: {JETSON_SEND_FREQUENCY_HZ} Hz (every {print_interval:.3f}s)")
    print("[JETSON] Starting continuous data collection (console output only)...")
    print("[JETSON] Press Ctrl+C to stop")

    while True:
        sample_count += 1
        print(f"time at {sample_count}")

        time.sleep(JETSON_READ_INTERVAL)

        thermal_data = read_jetson_thermal_zones()

        if not thermal_data and SIMULATE_SENSOR:
            thermal_data = {f'zone_{i}': round(40.0 + i, 2) for i in range(min(MAX_THERMAL_ZONES, 4))}
        elif not thermal_data:
            thermal_data = {f'zone_{i}': 0 for i in range(min(MAX_THERMAL_ZONES, 4))}

        samples_read += 1
        samples_since_print += 1

        current_time = time.time()
        time_since_last_print = current_time - last_print_time

        if samples_since_print >= JETSON_SEND_EVERY and time_since_last_print >= print_interval:
            samples_printed += 1
            print_data_locally(thermal_data, samples_printed, samples_read)
            samples_since_print = 0
            last_print_time = current_time
        else:
            print("[BUFFERED]", end="")
            for zone_id in range(MAX_THERMAL_ZONES):
                zone_key = f'zone_{zone_id}'
                if zone_key in thermal_data:
                    print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
            print(" (not yet printed)")

except KeyboardInterrupt:
    elapsed_time = time.time() - start_real_time
    print(f"\n[JETSON] Logging stopped after {elapsed_time:.2f} seconds")
    print(f"[JETSON] Total samples read: {samples_read}")
    print(f"[JETSON] Total samples printed: {samples_printed}")
    if samples_read > 0:
        print(f"[JETSON] Reduction: {100 * (1 - samples_printed/samples_read):.1f}%")
    print("[JETSON] All data was printed locally to the console")
except Exception as e:
    print(f"[JETSON] Error: {e}")
    sys.exit(1)
