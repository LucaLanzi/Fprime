import socket
import json
import os
import struct
from datetime import datetime
import threading
import sys
from pathlib import Path

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

from config_server import (
    SERVER_LISTEN_IP, SERVER_PORT, SERVER_OUTPUT_FILE, DEBUG, TIMESTAMP_FORMAT,
    SOCKET_BUFFER_SIZE, SOCKET_TIMEOUT
)
from config_imx8 import SENSORS_INA260, SENSORS_MCP9808

# Lock for thread-safe file writes (protects both file creation and writes)
file_lock = threading.Lock()

# Device-specific file locks stored by device_id
device_file_locks = {}

def get_output_file(device_id):
    """
    Generates device-specific output file path.
    
    Args:
        device_id: Device identifier (e.g., 'imx8', 'jetson')
    
    Returns:
        str: Path to device-specific CSV file
    """
    output_dir = os.path.dirname(SERVER_OUTPUT_FILE) or '.'
    base_name = os.path.splitext(os.path.basename(SERVER_OUTPUT_FILE))[0]
    return os.path.join(output_dir, f"{base_name}_{device_id}.csv")

def get_device_lock(device_id):
    """
    Get or create a lock for a specific device.
    Uses global lock to ensure thread-safe lock creation.
    """
    global device_file_locks
    if device_id not in device_file_locks:
        with file_lock:
            # Double-check pattern to avoid race condition
            if device_id not in device_file_locks:
                device_file_locks[device_id] = threading.Lock()
    return device_file_locks[device_id]


def get_csv_header(device_id):
    """
    Generates device-specific CSV header row.
    - IMX8: INA260 power + MCP9808 temperature + IMX8 CPU temperature
    - Jetson: Jetson thermal zones only
    
    Args:
        device_id: Device identifier to determine header format
    
    Returns:
        str: CSV header line
    """
    header_parts = ['server_timestamp']
    
    if device_id == 'imx8':
        # IMX8: Add INA260 and MCP9808 data
        # Add INA260 headers (power monitoring)
        for sensor_name in SENSORS_INA260:
            header_parts.append(f"{sensor_name}_voltage_V")
            header_parts.append(f"{sensor_name}_current_mA")
            header_parts.append(f"{sensor_name}_power_mW")
        
        # Add MCP9808 (temperature) headers
        for sensor_name in SENSORS_MCP9808:
            header_parts.append(f"{sensor_name}_temp_C")
        
        # Add IMX8 CPU temperature header
        header_parts.append("imx8_cpu_temp_C")
    
    else:
        # Jetson: Add thermal zone headers only
        for zone_id in range(10):  # Support up to 10 thermal zones
            header_parts.append(f"jetson_thermal_zone{zone_id}_C")
    
    header_parts.append('client_time')
    return ','.join(header_parts)

def initialize_output_file(device_id):
    """
    Create device-specific CSV file with device-specific headers if it doesn't exist.
    Uses device-specific lock to ensure thread-safe initialization.
    
    Args:
        device_id: Device identifier for the output file
    """
    output_file = get_output_file(device_id)
    device_lock = get_device_lock(device_id)
    
    with device_lock:
        if not os.path.exists(output_file):
            with open(output_file, 'w') as f:
                f.write(get_csv_header(device_id) + '\n')
            print(f"Created new file: {output_file}")
        else:
            print(f"Appending to existing file: {output_file}")

def save_data(timestamp, data):
    """
    Saves received sensor data to device-specific CSV file with server timestamp.
    Uses device-specific lock for thread-safe file writes and immediate fsync.
    
    Args:
        timestamp: Server's timestamp (time authority)
        data: Dictionary with keys 'sensors', 'client_time', 'device_id'
    """
    try:
        client_time = data.get('client_time', 'N/A')
        device_id = data.get('device_id', 'unknown')
        sensors_data = data.get('sensors', {})
        ina260_data = sensors_data.get('ina260', {})
        mcp9808_data = sensors_data.get('mcp9808', {})
        imx8_data = sensors_data.get('imx8', {})
        jetson_data = sensors_data.get('jetson_thermal', {})
        
        # Initialize file for this device if needed
        initialize_output_file(device_id)
        output_file = get_output_file(device_id)
        device_lock = get_device_lock(device_id)
        
        # Build device-specific CSV row (device_id is implicit in filename)
        row_parts = [timestamp]
        
        if device_id == 'imx8':
            # IMX8: Add INA260 and MCP9808 data only
            # Add INA260 data for each sensor in order
            for sensor_name in SENSORS_INA260:
                if sensor_name in ina260_data:
                    sensor_info = ina260_data[sensor_name]
                    row_parts.append(str(sensor_info.get('voltage', 0)))
                    row_parts.append(str(sensor_info.get('current', 0)))
                    row_parts.append(str(sensor_info.get('power', 0)))
                else:
                    # Add empty columns if sensor not present
                    row_parts.extend(['', '', ''])
            
            # Add MCP9808 (temperature) data for each sensor in order
            for sensor_name in SENSORS_MCP9808:
                if sensor_name in mcp9808_data:
                    sensor_info = mcp9808_data[sensor_name]
                    row_parts.append(str(sensor_info.get('temp_c', 0)))
                else:
                    row_parts.append('')
            
            # Add IMX8 CPU temperature
            row_parts.append(str(imx8_data.get('temp_c', 0) if imx8_data else ''))
        
        else:
            # Jetson: Add thermal zones only
            for zone_id in range(10):
                zone_key = f'zone_{zone_id}'
                zone_temp = jetson_data.get(zone_key, '') if jetson_data else ''
                row_parts.append(str(zone_temp))
        
        row_parts.append(client_time)
        row = ','.join(row_parts) + '\n'
        
        # Device-specific thread-safe file write
        with device_lock:
            with open(output_file, 'a') as f:
                f.write(row)
                f.flush()
                os.fsync(f.fileno())
        
        # Print summary
        print(f"[{device_id}] {timestamp}", end="")
        # Print INA260 data
        for sensor_name in SENSORS_INA260:
            if sensor_name in ina260_data:
                info = ina260_data[sensor_name]
                print(f" | {sensor_name}:V{info.get('voltage', 0)}V,I{info.get('current', 0)}mA,P{info.get('power', 0)}mW", end="")
        # Print MCP9808 data
        for sensor_name in SENSORS_MCP9808:
            if sensor_name in mcp9808_data:
                info = mcp9808_data[sensor_name]
                print(f" | {sensor_name}:T{info.get('temp_c', 0)}C", end="")
        # Print IMX8 CPU temperature
        if imx8_data:
            print(f" | IMX8_CPU:T{imx8_data.get('temp_c', 0)}C", end="")
        # Print Jetson thermal zones
        if jetson_data:
            for zone_id in range(10):
                zone_key = f'zone_{zone_id}'
                if zone_key in jetson_data:
                    print(f" | Zone{zone_id}:{jetson_data[zone_key]}C", end="")
        print()
    except Exception as e:
        print(f"Error saving data: {e}")

def handle_client(client_socket, client_address):
    """
    Handles a single client connection in a separate thread.
    Sends ready handshake on connection, then receives and saves data.
    
    Args:
        client_socket: The connected socket
        client_address: Client address tuple (ip, port)
    """
    client_socket.settimeout(SOCKET_TIMEOUT)
    
    print(f"[NEW CONNECTION] from {client_address}")
    
    try:
        # Send handshake/ready message to indicate server is ready to receive
        handshake = json.dumps({'status': 'ready', 'message': 'Server ready to receive data'}) + '\n'
        client_socket.sendall(handshake.encode('utf-8'))
        if DEBUG:
            print(f"[HANDSHAKE SENT] to {client_address}")
        
        data_buffer = b""
        while True:
            chunk = client_socket.recv(SOCKET_BUFFER_SIZE)
            if not chunk:
                break
            data_buffer += chunk
            
            # Check if we have a complete JSON message (ends with newline)
            if b'\n' in data_buffer:
                message = data_buffer.decode('utf-8').strip()
                data_buffer = b""
                
                # Parse and save JSON data
                if message:
                    try:
                        sensor_data = json.loads(message)
                        # Get SERVER's timestamp in Excel-compatible format (time authority)
                        server_timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
                        
                        # Save with server timestamp
                        save_data(server_timestamp, sensor_data)
                        
                        # Send acknowledgment back to client
                        response = json.dumps({'timestamp': server_timestamp}) + '\n'
                        client_socket.sendall(response.encode('utf-8'))
                        
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON from {client_address}: {e}")
                    except Exception as e:
                        print(f"Error processing data from {client_address}: {e}")
    
    except socket.timeout:
        print(f"[TIMEOUT] {client_address}")
    except Exception as e:
        print(f"Error in client handler for {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"[DISCONNECTED] {client_address}")


def start_server():
    """
    Start TCP server to receive and save sensor data from multiple clients.
    Uses threading to handle concurrent connections.
    Server provides timestamp (time authority) for all clients.
    Per-device CSV files are created on first data arrival from each device.
    """
    
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Set SO_LINGER to close socket immediately without TIME_WAIT
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    server_socket.bind((SERVER_LISTEN_IP, SERVER_PORT))
    server_socket.listen(5)
    
    if DEBUG:
        print(f"[SERVER] Configuration loaded from config.py")
    
    print(f"TIME AUTHORITY SERVER listening on {SERVER_LISTEN_IP}:{SERVER_PORT}")
    print(f"[SERVER] Output files: {os.path.dirname(SERVER_OUTPUT_FILE) or '.'}/received_data_*.csv")
    print(f"[SERVER] Multi-threaded server - handles multiple simultaneous clients")
    print("Waiting for data from clients...")
    
    try:
        while True:
            # Accept incoming connection
            client_socket, client_address = server_socket.accept()
            
            # Handle client in a separate thread
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
    
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()
        print("[SERVER] Server stopped")

if __name__ == "__main__":
    start_server()
