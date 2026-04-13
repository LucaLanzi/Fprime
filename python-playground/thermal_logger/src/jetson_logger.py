import random
import time
import datetime
import socket
import json
import os
import sys

import sys
from pathlib import Path

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

# Import Jetson-specific configuration
from config_jetson import (
    JETSON_SERVER_IP, JETSON_SERVER_PORT, JETSON_NUM_READINGS,
    JETSON_READ_INTERVAL, JETSON_CLIENT_DEVICE_ID, JETSON_OUTPUT_FILE,
    DEBUG, SIMULATE_SENSOR, TIMESTAMP_FORMAT, JETSON_THERMAL_ZONE_PATHS,
    MAX_THERMAL_ZONES, JETSON_SAVE_EVERY, NETWORK_TIMEOUT
)

# Update the output file directory
output_dir = os.path.dirname(JETSON_OUTPUT_FILE)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)


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
    if SIMULATE_SENSOR:
        # Simulate Jetson thermal zones with realistic temperatures
        thermal_data = {}
        for zone_id in range(10):
            # Simulate different temperature ranges for different zones
            if zone_id == 0:  # GPU - typically runs hot
                thermal_data[f'zone_{zone_id}'] = round(random.uniform(50.0, 90.0), 2)
            elif zone_id == 1:  # System - moderate temperatures
                thermal_data[f'zone_{zone_id}'] = round(random.uniform(40.0, 70.0), 2)
            else:  # Other zones - lower temps
                thermal_data[f'zone_{zone_id}'] = round(random.uniform(35.0, 60.0), 2)
        return thermal_data
    
    thermal_data = {}
    
    for zone_id, sensor_path in enumerate(JETSON_THERMAL_ZONE_PATHS):
        try:
            with open(sensor_path, 'r') as f:
                temp_millidegrees = int(f.read().strip())
                # Convert from millidegrees to degrees Celsius
                temp_celsius = temp_millidegrees / 1000.0
                thermal_data[f'zone_{zone_id}'] = round(temp_celsius, 2)
        except FileNotFoundError:
            # Zone not available on this system
            continue
        except Exception as e:
            if DEBUG:
                print(f"Error reading thermal zone {zone_id} from {sensor_path}: {e}")
            continue
    
    if DEBUG and not thermal_data:
        print("Warning: Could not read any Jetson thermal zones. Check paths and permissions.")
    
    return thermal_data


def send_data_over_network(thermal_data):
    """
    Sends Jetson thermal data over TCP to the receiver program.
    
    Args:
        thermal_data: Dict with thermal zone data
        
    Returns:
        tuple: (server_timestamp, success_flag)
    """
    try:
        # Create socket and connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(NETWORK_TIMEOUT)  # Timeout from config
        sock.connect((JETSON_SERVER_IP, JETSON_SERVER_PORT))
        
        # Create data packet as JSON with device identification
        data_packet = {
            'device_id': JETSON_CLIENT_DEVICE_ID,
            'sensors': {
                'jetson_thermal': thermal_data
            },
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
        print(f"Warning: Could not connect to server at {JETSON_SERVER_IP}:{JETSON_SERVER_PORT}")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False
    except socket.timeout:
        print("Warning: Server connection timeout.")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False
    except Exception as e:
        print(f"Warning: Network error: {e}")
        return datetime.datetime.now().strftime(TIMESTAMP_FORMAT), False


def get_csv_header():
    """
    Generates CSV header row for Jetson thermal zones.
    
    Returns:
        str: CSV header line
    """
    header_parts = ['timestamp', 'device_id']
    
    # Add empty columns for INA260 and MCP9808 (for CSV compatibility)
    header_parts.extend(['obc_voltage_V', 'obc_current_mA', 'obc_power_mW',
                        'perif_voltage_V', 'perif_current_mA', 'perif_power_mW',
                        'jetson_voltage_V', 'jetson_current_mA', 'jetson_power_mW',
                        'obc_temp_C', 'perif_temp_C', 'jetson_temp_C',
                        'imx8_cpu_temp_C'])
    
    # Add Jetson thermal zone headers
    for zone_id in range(10):
        header_parts.append(f"jetson_thermal_zone{zone_id}_C")
    
    header_parts.append('client_time')
    return ', '.join(header_parts)


def appender_local(timestamp, device_id, thermal_data, output_file=None):
    """
    Appends Jetson thermal data to local CSV file (for local logging).
    
    Args:
        timestamp: Timestamp string
        device_id: Device identifier
        thermal_data: Dict with thermal zone data
        output_file: Optional custom output file path
    """
    if output_file is None:
        output_file = JETSON_OUTPUT_FILE
    
    try:
        file = open(output_file, "a")
        
        # Build CSV row
        row_parts = [timestamp, device_id]
        
        # Add empty columns for INA260 and MCP9808 (for CSV compatibility)
        row_parts.extend(['', '', '',
                         '', '', '',
                         '', '', '',
                         '', '', '',
                         ''])
        
        # Add Jetson thermal zone data
        for zone_id in range(10):
            zone_key = f'zone_{zone_id}'
            row_parts.append(str(thermal_data.get(zone_key, '')))
        
        row = ', '.join(row_parts) + '\n'
        file.write(row)
        file.close()
        
        return 0
    except Exception as e:
        print(f"Error writing to file: {e}")
        return -1


# Main program
try:
    # Generate timestamped output filename
    run_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.dirname(JETSON_OUTPUT_FILE)
    output_basename = os.path.basename(JETSON_OUTPUT_FILE)
    output_name_without_ext = os.path.splitext(output_basename)[0]
    output_ext = os.path.splitext(output_basename)[1] or '.csv'
    timestamped_output_file = os.path.join(output_dir, f"{output_name_without_ext}_{run_timestamp}{output_ext}")
    
    if DEBUG:
        print(f"[JETSON] Connecting to server at {JETSON_SERVER_IP}:{JETSON_SERVER_PORT}")
        print(f"[JETSON] Taking {JETSON_NUM_READINGS} readings")
        print(f"[JETSON] Sampling: Reading every {JETSON_READ_INTERVAL}s")
    
    # Initialize I2C bus or simulation mode
    if SIMULATE_SENSOR:
        print("[JETSON] *** SIMULATION MODE ENABLED ***")
        print("[JETSON] Using synthetic thermal sensor data for testing")
    
    # Initialize CSV file with header (using timestamped filename)
    if not os.path.exists(timestamped_output_file):
        with open(timestamped_output_file, 'w') as f:
            f.write(get_csv_header() + '\n')
        if DEBUG:
            print(f"[JETSON] Created new CSV file: {timestamped_output_file}")
    
    samples_read = 0
    samples_saved = 0
    samples_since_save = 0  # Counter for sampling control
    
    start_real_time = time.time()
    for x in range(JETSON_NUM_READINGS):
        current_time = x + 1
        print(f"time at {current_time}")
        
        # Simulate time passing
        time.sleep(JETSON_READ_INTERVAL)
        
        # Read all Jetson thermal zones
        thermal_data = read_jetson_thermal_zones()
        
        samples_read += 1
        samples_since_save += 1
        
        # Check if we should save this sample
        if samples_since_save >= JETSON_SAVE_EVERY:
            # Send over network and get server timestamp
            server_timestamp, sync_success = send_data_over_network(thermal_data)
            
            # Use server timestamp for local storage
            if server_timestamp:
                appender_local(server_timestamp, JETSON_CLIENT_DEVICE_ID, thermal_data, timestamped_output_file)
                sync_status = "[SYNCED]" if sync_success else "[LOCAL FALLBACK]"
            else:
                local_timestamp = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
                appender_local(local_timestamp, JETSON_CLIENT_DEVICE_ID, thermal_data, timestamped_output_file)
                sync_status = "[NO SYNC]"
            
            samples_saved += 1
            samples_since_save = 0  # Reset counter
            
            # Print with save indicator
            print(f"{sync_status} [SAVED {samples_saved}]", end="")
            # Print thermal zone data
            for zone_id in range(MAX_THERMAL_ZONES):
                zone_key = f'zone_{zone_id}'
                if zone_key in thermal_data:
                    print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
            print()
        else:
            # Read but don't save
            print(f"[SKIPPED]", end="")
            # Print thermal zone data
            for zone_id in range(MAX_THERMAL_ZONES):
                zone_key = f'zone_{zone_id}'
                if zone_key in thermal_data:
                    print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
            print(" (buffered, not sent)")
    
    # Print summary
    end_real_time = time.time()
    elapsed_time = end_real_time - start_real_time
    
    print(f"\n[JETSON] Completed after {elapsed_time:.2f} seconds")
    print(f"[JETSON] Samples read: {samples_read}, saved: {samples_saved}")
    print(f"[JETSON] Local file: {timestamped_output_file}")

except KeyboardInterrupt:
    print("\n[JETSON] Interrupted by user")
except Exception as e:
    print(f"[JETSON] Error: {e}")
    sys.exit(1)
