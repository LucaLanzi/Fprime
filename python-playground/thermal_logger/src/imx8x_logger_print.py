import time
import datetime
import os

try:
    import smbus2
except ImportError:
    smbus2 = None

import sys
from pathlib import Path

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

from config_imx8 import (
    I2C_BUS,
    NUM_READINGS, READ_INTERVAL, DEBUG, SEND_EVERY, SEND_FREQUENCY_HZ,
    SIMULATE_SENSOR, INA260_BUS_VOLTAGE, INA260_CURRENT, INA260_POWER,
    TIMESTAMP_FORMAT, SENSORS_INA260, SENSORS_MCP9808, MCP9808_REG_TEMP,
    IMX8_TEMP_SENSOR_PATH, IMX8_TEMP_SENSOR_FALLBACK_PATHS
)


def _read_swapped_word(bus, address, register):
    """Read a 16-bit SMBus word and normalize it to sensor byte order."""
    raw_value = bus.read_word_data(address, register)
    return ((raw_value << 8) & 0xFF00) | ((raw_value >> 8) & 0x00FF)


def read_single_ina260(bus, address):
    try:
        voltage_raw = _read_swapped_word(bus, address, INA260_BUS_VOLTAGE)
        voltage = ((voltage_raw & 0xFFFF) >> 3) * 1.25 / 1000

        current_raw = _read_swapped_word(bus, address, INA260_CURRENT)
        if current_raw & 0x8000:
            current_raw -= 0x10000
        current = current_raw * 1.25

        power_raw = _read_swapped_word(bus, address, INA260_POWER)
        power = (power_raw & 0xFFFF) * 10

        return {
            'voltage': round(voltage, 3),
            'current': round(current, 2),
            'power': round(power, 1)
        }
    except Exception as e:
        print(f"Error reading INA260 at address 0x{address:02x}: {e}")
        return {'voltage': 0, 'current': 0, 'power': 0}


def read_all_ina260_sensors(bus):
    all_data = {}
    for sensor_name, sensor_config in SENSORS_INA260.items():
        address = sensor_config['address']
        all_data[sensor_name] = read_single_ina260(bus, address)
    return all_data


def read_single_mcp9808(bus, address):
    try:
        temp_raw = _read_swapped_word(bus, address, MCP9808_REG_TEMP)
        temp_raw &= 0x1FFF

        temperature = temp_raw / 16.0
        if temp_raw & 0x1000:
            temperature -= 256.0

        return {'temp_c': round(temperature, 2)}
    except Exception as e:
        print(f"Error reading MCP9808 at address 0x{address:02x}: {e}")
        return {'temp_c': 0}


def read_all_mcp9808_sensors(bus):
    all_data = {}
    for sensor_name, sensor_config in SENSORS_MCP9808.items():
        address = sensor_config['address']
        all_data[sensor_name] = read_single_mcp9808(bus, address)
    return all_data


def read_imx8_cpu_temperature():
    sensor_paths = [IMX8_TEMP_SENSOR_PATH] + IMX8_TEMP_SENSOR_FALLBACK_PATHS

    for sensor_path in sensor_paths:
        try:
            with open(sensor_path, 'r') as f:
                temp_millidegrees = int(f.read().strip())
                temp_celsius = temp_millidegrees / 1000.0
                return {'temp_c': round(temp_celsius, 2)}
        except FileNotFoundError:
            continue
        except Exception as e:
            if DEBUG:
                print(f"Error reading IMX8 temperature from {sensor_path}: {e}")
            continue

    if DEBUG:
        print(f"Warning: Could not read IMX8 CPU temperature from any sensor path. Tried: {sensor_paths}")

    return {'temp_c': 0}


def format_sensor_line(sample_number, timestamp, all_sensor_data, printed_count):
    parts = [f"[PRINTED] [SAMPLE {printed_count}] [READ {sample_number}] [{timestamp}]"]

    ina260_data = all_sensor_data.get('ina260', {})
    for sensor_name in SENSORS_INA260:
        data = ina260_data.get(sensor_name, {})
        parts.append(
            f"{sensor_name}:V{data.get('voltage', 0)}V,"
            f"I{data.get('current', 0)}mA,"
            f"P{data.get('power', 0)}mW"
        )

    mcp9808_data = all_sensor_data.get('mcp9808', {})
    for sensor_name in SENSORS_MCP9808:
        data = mcp9808_data.get(sensor_name, {})
        parts.append(f"{sensor_name}:T{data.get('temp_c', 0)}C")

    imx8_data = all_sensor_data.get('imx8', {})
    parts.append(f"IMX8_CPU:T{imx8_data.get('temp_c', 0)}C")

    return " ".join(parts)


# main program here
bus = None
samples_read = 0
samples_printed = 0
start_real_time = time.time()
sample_count = 0

try:
    print("[CLIENT] *** LOCAL PRINT MODE - No server connection, no remote logging ***")

    if DEBUG:
        print(f"[CLIENT] Using I2C bus {I2C_BUS}, target readings: {NUM_READINGS}")
        print(f"[CLIENT] Sampling: Reading every {READ_INTERVAL}s, Printing every {SEND_EVERY} sample(s)")
        print(f"[CLIENT] INA260 Power Sensors configured:")
        for sensor_name, config in SENSORS_INA260.items():
            print(f"        - {sensor_name:10} (0x{config['address']:02x}): {config['description']}")
        print(f"[CLIENT] MCP9808 Temperature Sensors configured:")
        for sensor_name, config in SENSORS_MCP9808.items():
            print(f"        - {sensor_name:10} (0x{config['address']:02x}): {config['description']}")

    if SIMULATE_SENSOR:
        print("[CLIENT] *** SIMULATION MODE ENABLED ***")
        print("[CLIENT] Using synthetic sensor data for testing")
        bus = None
    else:
        try:
            if smbus2 is None:
                raise RuntimeError("smbus2 is not installed")
            bus = smbus2.SMBus(I2C_BUS)
            print(f"[CLIENT] Successfully opened I2C bus {I2C_BUS}")
        except Exception as e:
            print(f"[CLIENT] Warning: Could not open I2C bus {I2C_BUS}: {e}")
            print("[CLIENT] Falling back to zero-value reads")
            bus = None

    print_interval = 1.0 / SEND_FREQUENCY_HZ if SEND_FREQUENCY_HZ > 0 else 0
    last_print_time = 0.0
    samples_since_print = 0

    print(f"[CLIENT] Print frequency limit: {SEND_FREQUENCY_HZ} Hz")
    print(f"[CLIENT] Starting continuous data collection (printing to screen)...")
    print(f"[CLIENT] Send SIGTERM (Ctrl+C) to stop")

    while True:
        sample_count += 1
        time.sleep(READ_INTERVAL)

        ina260_data = read_all_ina260_sensors(bus) if bus is not None else {
            sensor_name: {'voltage': 0, 'current': 0, 'power': 0}
            for sensor_name in SENSORS_INA260
        }
        mcp9808_data = read_all_mcp9808_sensors(bus) if bus is not None else {
            sensor_name: {'temp_c': 0}
            for sensor_name in SENSORS_MCP9808
        }
        imx8_data = read_imx8_cpu_temperature()

        all_sensor_data = {
            'ina260': ina260_data,
            'mcp9808': mcp9808_data,
            'imx8': imx8_data
        }

        samples_read += 1
        samples_since_print += 1
        current_time = time.time()
        time_since_last_print = current_time - last_print_time

        should_print = samples_since_print >= SEND_EVERY
        if print_interval > 0:
            should_print = should_print and time_since_last_print >= print_interval

        if should_print:
            samples_printed += 1
            samples_since_print = 0
            last_print_time = current_time
            timestamp = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
            print(format_sensor_line(sample_count, timestamp, all_sensor_data, samples_printed))
        else:
            print(f"[BUFFERED] [READ {sample_count}] Waiting for next print window")

except KeyboardInterrupt:
    pass
finally:
    elapsed_time = time.time() - start_real_time
    print(f"\n[CLIENT] Logging stopped after {elapsed_time:.2f} seconds")
    print(f"[CLIENT] Total samples read: {samples_read}")
    print(f"[CLIENT] Total samples printed: {samples_printed}")
    if samples_read > 0:
        print(f"[CLIENT] Reduction: {100 * (1 - samples_printed / samples_read):.1f}%")
    print(f"[CLIENT] Data was printed locally to the console")
    if bus is not None:
        bus.close()
