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
    JETSON_READ_INTERVAL, JETSON_CLIENT_DEVICE_ID,
    DEBUG, SIMULATE_SENSOR, TIMESTAMP_FORMAT, JETSON_THERMAL_ZONE_PATHS,
    MAX_THERMAL_ZONES, JETSON_SEND_EVERY, JETSON_SEND_FREQUENCY_HZ, NETWORK_TIMEOUT
)

# No local logging - all data sent to remote server


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
    
    print(f"[JETSON] Waiting for server at {JETSON_SERVER_IP}:{JETSON_SERVER_PORT}...")
    
    while time.time() - start_time < max_wait_time:
        attempt += 1
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((JETSON_SERVER_IP, JETSON_SERVER_PORT))
            
            # Wait for handshake/ready message from server
            response = sock.recv(1024).decode('utf-8').strip()
            sock.close()
            
            if response:
                try:
                    response_data = json.loads(response)
                    if response_data.get('status') == 'ready':
                        print(f"[JETSON] Server handshake received! Server is ready! (attempt {attempt})")
                        return True
                except json.JSONDecodeError:
                    pass
            
            elapsed = time.time() - start_time
            print(f"[JETSON] Attempt {attempt}: Handshake not complete... (elapsed: {elapsed:.0f}s)")
            time.sleep(retry_interval)
            
        except (ConnectionRefusedError, socket.timeout, OSError):
            elapsed = time.time() - start_time
            print(f"[JETSON] Attempt {attempt}: Server not ready yet... (elapsed: {elapsed:.0f}s)")
            time.sleep(retry_interval)
        except Exception as e:
            print(f"[JETSON] Connection error: {e}")
            time.sleep(retry_interval)
    
    print(f"[JETSON] Error: Server did not become available within {max_wait_time} seconds")
    return False


# Main program
try:
    # Wait for server to be available before starting
    if not wait_for_server():
        print("[JETSON] Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print("[JETSON] *** REMOTE LOGGING ONLY - No local logging ***")
    
    if DEBUG:
        print(f"[JETSON] Connecting to server at {JETSON_SERVER_IP}:{JETSON_SERVER_PORT}")
        print(f"[JETSON] Taking {JETSON_NUM_READINGS} readings")
        print(f"[JETSON] Sampling: Reading every {JETSON_READ_INTERVAL}s, Sending every {JETSON_SEND_EVERY} sample(s)")
    
    # Initialize simulation mode info
    if SIMULATE_SENSOR:
        print("[JETSON] *** SIMULATION MODE ENABLED ***")
        print("[JETSON] Using synthetic thermal sensor data for testing")
    
    # Calculate send interval based on frequency (times per second)
    send_interval = 1.0 / JETSON_SEND_FREQUENCY_HZ if JETSON_SEND_FREQUENCY_HZ > 0 else float('inf')
    last_send_time = time.time()
    
    samples_read = 0
    samples_sent = 0
    samples_since_send = 0  # Counter for sampling control
    
    start_real_time = time.time()
    sample_count = 0  # Counter for display purposes
    
    print(f"[JETSON] Send frequency: {JETSON_SEND_FREQUENCY_HZ} Hz (every {send_interval:.3f}s)")
    print(f"[JETSON] Starting continuous data collection (remote logging only)...")
    print(f"[JETSON] Send SIGTERM (Ctrl+C) to stop logging")
    
    while True:
        sample_count += 1
        print(f"time at {sample_count}")
        
        # Simulate time passing
        time.sleep(JETSON_READ_INTERVAL)
        
        # Read all Jetson thermal zones
        thermal_data = read_jetson_thermal_zones()
        
        samples_read += 1
        samples_since_send += 1
        
        # Check if it's time to send based on frequency rate limiting and decimation
        current_time = time.time()
        time_since_last_send = current_time - last_send_time
        
        # Send if: (1) decimation counter reached AND (2) enough time has passed
        if samples_since_send >= JETSON_SEND_EVERY and time_since_last_send >= send_interval:
            # Send over network to remote server for logging
            server_timestamp, sync_success = send_data_over_network(thermal_data)
            
            sync_status = "[SENT]" if sync_success else "[SEND FAILED]"
            
            samples_sent += 1
            samples_since_send = 0  # Reset counter
            last_send_time = current_time  # Update last send time for frequency control
            
            # Print with send indicator
            print(f"{sync_status} [SENT {samples_sent}]", end="")
            # Print thermal zone data
            for zone_id in range(MAX_THERMAL_ZONES):
                zone_key = f'zone_{zone_id}'
                if zone_key in thermal_data:
                    print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
            print()
        else:
            # Read but don't send
            print(f"[BUFFERED]", end="")
            # Print thermal zone data
            for zone_id in range(MAX_THERMAL_ZONES):
                zone_key = f'zone_{zone_id}'
                if zone_key in thermal_data:
                    print(f" Zone{zone_id}:{thermal_data[zone_key]}C", end="")
            print(" (not yet sent)")

except KeyboardInterrupt:
    elapsed_time = time.time() - start_real_time
    print(f"\n[JETSON] Logging stopped after {elapsed_time:.2f} seconds")
    print(f"[JETSON] Total samples read: {samples_read}")
    print(f"[JETSON] Total samples sent to server: {samples_sent}")
    if samples_read > 0:
        print(f"[JETSON] Reduction: {100 * (1 - samples_sent/samples_read):.1f}%")
    print(f"[JETSON] All data logged remotely on receiver machine")
except Exception as e:
    print(f"[JETSON] Error: {e}")
    sys.exit(1)
