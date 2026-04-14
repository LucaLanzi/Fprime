import random
import time
import datetime
import socket
import json
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
    SERVER_IP, SERVER_PORT, I2C_BUS,
    NUM_READINGS, READ_INTERVAL, DEBUG, SEND_EVERY, SEND_FREQUENCY_HZ,
    SIMULATE_SENSOR, INA260_BUS_VOLTAGE, INA260_CURRENT, INA260_POWER,
    TIMESTAMP_FORMAT, SENSORS_INA260, SENSORS_MCP9808, MCP9808_REG_TEMP,
    IMX8_TEMP_SENSOR_PATH, IMX8_TEMP_SENSOR_FALLBACK_PATHS, CLIENT_DEVICE_ID,
    NETWORK_TIMEOUT
)

# No local logging - all data sent to remote server

def read_single_ina260(bus, address):
    """
    Reads data from a single INA260 sensor.
    
    Args:
        bus: smbus2.SMBus object or None for simulation
        address: I2C address of the sensor
        
    Returns:
        dict: Parsed sensor data with keys 'voltage', 'current', 'power'
    """
    if SIMULATE_SENSOR or bus is None:
        return {
            'voltage': round(random.uniform(4.8, 5.2), 3),
            'current': round(random.uniform(200, 400), 2),
            'power': round(random.uniform(1000, 2000), 1)
        }
    
    try:
        voltage_raw = bus.read_word_data(address, INA260_BUS_VOLTAGE)
        voltage = ((voltage_raw & 0xFFFF) >> 3) * 1.25 / 1000
        
        current_raw = bus.read_word_data(address, INA260_CURRENT)
        current = (current_raw & 0xFFFF) * 1.25
        
        power_raw = bus.read_word_data(address, INA260_POWER)
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
    """
    Reads data from all configured INA260 sensors.
    
    Args:
        bus: smbus2.SMBus object or None for simulation
        
    Returns:
        dict: Sensor data organized by sensor name
              Format: {
                  'obc': {'voltage': X, 'current': Y, 'power': Z},
                  'perif': {'voltage': X, 'current': Y, 'power': Z},
                  'jetson': {'voltage': X, 'current': Y, 'power': Z}
              }
    """
    all_data = {}
    
    for sensor_name, sensor_config in SENSORS_INA260.items():
        address = sensor_config['address']
        all_data[sensor_name] = read_single_ina260(bus, address)
    
    return all_data


def read_ina260_data(bus):
    """
    Deprecated: Use read_all_ina260_sensors() instead.
    Kept for backward compatibility.
    """
    return read_all_ina260_sensors(bus)


def read_single_mcp9808(bus, address):
    """
    Reads temperature from a single MCP9808 sensor.
    
    Args:
        bus: smbus2.SMBus object or None for simulation
        address: I2C address of the sensor
        
    Returns:
        dict: Temperature data with key 'temp_c' (Celsius)
    """
    if SIMULATE_SENSOR or bus is None:
        return {
            'temp_c': round(random.uniform(20.0, 60.0), 2)  # Simulate 20-60°C
        }
    
    try:
        # Read temperature register (0x05)
        temp_raw = bus.read_word_data(address, MCP9808_REG_TEMP)
        
        # MCP9808 temperature format:
        # Upper byte: integer part
        # Lower byte: fractional part (1/16°C resolution)
        upper = (temp_raw >> 8) & 0xFF
        lower = temp_raw & 0xFF
        
        # Extract sign bit
        sign_bit = (upper >> 7) & 1
        
        # Extract integer part (bits 4-6 of upper byte)
        int_part = upper & 0x0F
        if sign_bit:
            # Handle negative temperatures (two's complement)
            int_part = -(~(int_part) & 0x0F) - 1
        
        # Extract fractional part (upper 4 bits of lower byte)
        frac_part = (lower >> 4) & 0x0F
        frac = frac_part / 16.0
        
        temperature = int_part + frac if sign_bit == 0 else int_part - frac
        
        return {
            'temp_c': round(temperature, 2)
        }
    except Exception as e:
        print(f"Error reading MCP9808 at address 0x{address:02x}: {e}")
        return {'temp_c': 0}


def read_all_mcp9808_sensors(bus):
    """
    Reads temperature data from all configured MCP9808 sensors.
    
    Args:
        bus: smbus2.SMBus object or None for simulation
        
    Returns:
        dict: Temperature data organized by sensor name
              Format: {
                  'obc': {'temp_c': X},
                  'perif': {'temp_c': Y},
                  'jetson': {'temp_c': Z}
              }
    """
    all_data = {}
    
    for sensor_name, sensor_config in SENSORS_MCP9808.items():
        address = sensor_config['address']
        all_data[sensor_name] = read_single_mcp9808(bus, address)
    
    return all_data


def read_imx8_cpu_temperature():
    """
    Reads IMX8 SoC CPU temperature from Linux thermal zone.
    
    The kernel exposes CPU temperature at /sys/class/thermal/thermal_zone0/temp
    Value is in millidegrees Celsius (divide by 1000 to get °C).
    
    Returns:
        dict: Temperature data with key 'temp_c' (Celsius)
              Format: {'temp_c': X}
    """
    if SIMULATE_SENSOR:
        # Simulate IMX8 CPU temperature (typically higher than ambient)
        return {
            'temp_c': round(random.uniform(40.0, 85.0), 2)
        }
    
    # Try primary path first
    sensor_paths = [IMX8_TEMP_SENSOR_PATH] + IMX8_TEMP_SENSOR_FALLBACK_PATHS
    
    for sensor_path in sensor_paths:
        try:
            with open(sensor_path, 'r') as f:
                temp_millidegrees = int(f.read().strip())
                # Convert from millidegrees to degrees Celsius
                temp_celsius = temp_millidegrees / 1000.0
                return {
                    'temp_c': round(temp_celsius, 2)
                }
        except FileNotFoundError:
            continue
        except Exception as e:
            if DEBUG:
                print(f"Error reading IMX8 temperature from {sensor_path}: {e}")
            continue
    
    # If no path worked, log warning and return 0
    if DEBUG:
        print(f"Warning: Could not read IMX8 CPU temperature from any sensor path. Tried: {sensor_paths}")
    
    return {
        'temp_c': 0
    }




def wait_for_server(max_wait_time=300):
    """
    Waits for the server to be available and ready before proceeding.
    Performs handshake to confirm server is ready to receive data.
    Retries connection attempts until successful or timeout.
    
    Args:
        max_wait_time: Maximum time to wait for server in seconds (default: 5 minutes)
        
    Returns:
        bool: True if server is available and handshakes, False if timeout reached
    """
    start_time = time.time()
    retry_interval = 2  # Retry every 2 seconds
    attempt = 0
    
    print(f"[CLIENT] Waiting for server at {SERVER_IP}:{SERVER_PORT}...")
    
    while time.time() - start_time < max_wait_time:
        attempt += 1
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((SERVER_IP, SERVER_PORT))
            
            # Wait for handshake/ready message from server
            response = sock.recv(1024).decode('utf-8').strip()
            sock.close()
            
            if response:
                try:
                    response_data = json.loads(response)
                    if response_data.get('status') == 'ready':
                        print(f"[CLIENT] Server handshake received! Server is ready! (attempt {attempt})")
                        return True
                except json.JSONDecodeError:
                    pass
            
            elapsed = time.time() - start_time
            print(f"[CLIENT] Attempt {attempt}: Handshake not complete... (elapsed: {elapsed:.0f}s)")
            time.sleep(retry_interval)
            
        except (ConnectionRefusedError, socket.timeout, OSError):
            elapsed = time.time() - start_time
            print(f"[CLIENT] Attempt {attempt}: Server not ready yet... (elapsed: {elapsed:.0f}s)")
            time.sleep(retry_interval)
        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            time.sleep(retry_interval)
    
    print(f"[CLIENT] Error: Server did not become available within {max_wait_time} seconds")
    return False


def send_data_over_network(sensor_data):
    """
    Sends sensor data over TCP to the receiver program.
    Receives server timestamp to ensure time synchronization.
    
    Args:
        sensor_data: Dict with data from all sensors
        
    Returns:
        tuple: (server_timestamp, success_flag) - Returns server's timestamp if successful
    """
    try:
        # Create socket and connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(NETWORK_TIMEOUT)  # Timeout from config
        sock.connect((SERVER_IP, SERVER_PORT))
        
        # Create data packet as JSON with device identification
        data_packet = {
            'device_id': CLIENT_DEVICE_ID,
            'sensors': sensor_data,
            'client_time': datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
        }
        
        # Send JSON data
        message = json.dumps(data_packet) + '\n'
        sock.sendall(message.encode('utf-8'))
        
        # Receive server timestamp
        response = sock.recv(1024).decode('utf-8').strip()
        sock.close()
        
        if response:
            server_data = json.loads(response)
            return server_data.get('timestamp'), True
        else:
            return None, False
        
    except ConnectionRefusedError:
        print(f"Warning: Could not connect to server at {SERVER_IP}:{SERVER_PORT}. Ensure receiver.py is running.")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False
    except socket.timeout:
        print("Warning: Server connection timeout.")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False
    except Exception as e:
        print(f"Warning: Network error: {e}")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False
            
# main program here
try:
    # Wait for server to be available before starting
    if not wait_for_server():
        print("[CLIENT] Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print("[CLIENT] *** REMOTE LOGGING ONLY - No local logging ***")
    
    if DEBUG:
        print(f"[CLIENT] Connecting to server at {SERVER_IP}:{SERVER_PORT}")
        print(f"[CLIENT] Using I2C bus {I2C_BUS}, taking {NUM_READINGS} readings")
        print(f"[CLIENT] Sampling: Reading every {READ_INTERVAL}s, Sending every {SEND_EVERY} sample(s)")
        print(f"[CLIENT] INA260 Power Sensors configured:")
        for sensor_name, config in SENSORS_INA260.items():
            print(f"        - {sensor_name:10} (0x{config['address']:02x}): {config['description']}")
        print(f"[CLIENT] MCP9808 Temperature Sensors configured:")
        for sensor_name, config in SENSORS_MCP9808.items():
            print(f"        - {sensor_name:10} (0x{config['address']:02x}): {config['description']}")
    
    # Initialize I2C bus or simulation mode
    bus = None
    if SIMULATE_SENSOR:
        print("[CLIENT] *** SIMULATION MODE ENABLED ***")
        print("[CLIENT] Using synthetic sensor data for testing")
        bus = None
    else:
        try:
            bus = smbus2.SMBus(I2C_BUS)
            print(f"[CLIENT] Successfully opened I2C bus {I2C_BUS}")
        except Exception as e:
            print(f"[CLIENT] Warning: Could not open I2C bus {I2C_BUS}: {e}")
            print("[CLIENT] Falling back to simulation mode")
    
    # Calculate send interval based on frequency (times per second)
    send_interval = 1.0 / SEND_FREQUENCY_HZ if SEND_FREQUENCY_HZ > 0 else float('inf')
    last_send_time = time.time()
    
    samples_since_send = 0  # Counter for sampling control
    samples_read = 0        # Total samples read
    samples_sent = 0        # Total samples sent to server
    
    start_real_time = time.time()
    sample_count = 0  # Counter for display purposes
    
    print(f"[CLIENT] Send frequency: {SEND_FREQUENCY_HZ} Hz (every {send_interval:.3f}s)")
    print(f"[CLIENT] Starting continuous data collection (remote logging only)...")
    print(f"[CLIENT] Send SIGTERM (Ctrl+C) to stop logging")
    
    while True:
        sample_count += 1
        print(f"time at {sample_count}")
        
        # Simulate time passing
        time.sleep(READ_INTERVAL)
        
        # Read all sensors (INA260 power + MCP9808 temperature + IMX8 CPU temperature)
        ina260_data = read_all_ina260_sensors(bus)
        mcp9808_data = read_all_mcp9808_sensors(bus)
        imx8_data = read_imx8_cpu_temperature()
        
        # Combine all sensor data
        all_sensor_data = {
            'ina260': ina260_data,
            'mcp9808': mcp9808_data,
            'imx8': imx8_data
        }
        
        samples_read += 1
        samples_since_send += 1
        
        # Check if it's time to send based on frequency rate limiting and decimation
        current_time = time.time()
        time_since_last_send = current_time - last_send_time
        
        # Send if: (1) decimation counter reached AND (2) enough time has passed
        if samples_since_send >= SEND_EVERY and time_since_last_send >= send_interval:
            # Send over network to remote server for logging
            server_timestamp, sync_success = send_data_over_network(all_sensor_data)
            
            sync_status = "[SENT]" if sync_success else "[SEND FAILED]"
            
            samples_sent += 1
            samples_since_send = 0  # Reset counter
            last_send_time = current_time  # Update last send time for frequency control
            
            # Print with send indicator
            print(f"{sync_status} [SENT {samples_sent}]", end="")
            # Print INA260 data
            ina260_data = all_sensor_data.get('ina260', {})
            for sensor_name in sorted(SENSORS_INA260.keys()):
                data = ina260_data.get(sensor_name, {})
                print(f" {sensor_name}:V{data.get('voltage', 0)}V,I{data.get('current', 0)}mA,P{data.get('power', 0)}mW", end="")
            # Print MCP9808 data
            mcp9808_data = all_sensor_data.get('mcp9808', {})
            for sensor_name in sorted(SENSORS_MCP9808.keys()):
                data = mcp9808_data.get(sensor_name, {})
                print(f" {sensor_name}:T{data.get('temp_c', 0)}C", end="")
            # Print IMX8 CPU temperature
            imx8_data = all_sensor_data.get('imx8', {})
            print(f" IMX8_CPU:T{imx8_data.get('temp_c', 0)}C", end="")
            print()
        else:
            # Read but don't send
            print(f"[BUFFERED]", end="")
            # Print INA260 data
            ina260_data = all_sensor_data.get('ina260', {})
            for sensor_name in sorted(SENSORS_INA260.keys()):
                data = ina260_data.get(sensor_name, {})
                print(f" {sensor_name}:V{data.get('voltage', 0)}V,I{data.get('current', 0)}mA", end="")
            # Print MCP9808 data
            mcp9808_data = all_sensor_data.get('mcp9808', {})
            for sensor_name in sorted(SENSORS_MCP9808.keys()):
                data = mcp9808_data.get(sensor_name, {})
                print(f" {sensor_name}:T{data.get('temp_c', 0)}C", end="")
            # Print IMX8 CPU temperature
            imx8_data = all_sensor_data.get('imx8', {})
            print(f" IMX8_CPU:T{imx8_data.get('temp_c', 0)}C", end="")
            print(" (not yet sent)")
        
finally:
    elapsed_time = time.time() - start_real_time
    print(f"\n[CLIENT] Logging stopped after {elapsed_time:.2f} seconds")
    print(f"[CLIENT] Total samples read: {samples_read}")
    print(f"[CLIENT] Total samples sent to server: {samples_sent}")
    if samples_read > 0:
        print(f"[CLIENT] Reduction: {100 * (1 - samples_sent/samples_read):.1f}%")
    print(f"[CLIENT] All data logged remotely on receiver machine")
    if bus is not None:
        bus.close()