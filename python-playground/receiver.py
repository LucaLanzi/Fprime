import socket
import json
import os
from datetime import datetime
from config import SERVER_LISTEN_IP, SERVER_PORT, SERVER_OUTPUT_FILE, DEBUG, TIMESTAMP_FORMAT, SENSORS_INA260, SENSORS_MCP9808

# CSV file path
OUTPUT_FILE = SERVER_OUTPUT_FILE


def get_csv_header():
    """
    Generates CSV header row for all sensors (INA260 power + MCP9808 temperature).
    
    Returns:
        str: CSV header line
    """
    header_parts = ['server_timestamp']
    
    # Add INA260 headers
    for sensor_name in sorted(SENSORS_INA260.keys()):
        header_parts.append(f"{sensor_name}_voltage_V")
        header_parts.append(f"{sensor_name}_current_mA")
        header_parts.append(f"{sensor_name}_power_mW")
    
    # Add MCP9808 (temperature) headers
    for sensor_name in sorted(SENSORS_MCP9808.keys()):
        header_parts.append(f"{sensor_name}_temp_C")
    
    header_parts.append('client_time')
    return ', '.join(header_parts)

def initialize_output_file():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'w') as f:
            f.write(get_csv_header() + '\n')
        print(f"Created new file: {OUTPUT_FILE}")
    else:
        print(f"Appending to existing file: {OUTPUT_FILE}")

def save_data(timestamp, data):
    """
    Saves received sensor data to CSV file with server timestamp.
    Uses immediate fsync to ensure data is written to disk (crash-safe).
    
    Args:
        timestamp: Server's timestamp (time authority)
        data: Dictionary with keys 'sensors' {'ina260': {...}, 'mcp9808': {...}} and 'client_time'
    """
    try:
        client_time = data.get('client_time', 'N/A')
        sensors_data = data.get('sensors', {})
        ina260_data = sensors_data.get('ina260', {})
        mcp9808_data = sensors_data.get('mcp9808', {})
        
        # Build CSV row
        row_parts = [timestamp]
        
        # Add INA260 data for each sensor in order
        for sensor_name in sorted(SENSORS_INA260.keys()):
            if sensor_name in ina260_data:
                sensor_info = ina260_data[sensor_name]
                row_parts.append(str(sensor_info.get('voltage', 0)))
                row_parts.append(str(sensor_info.get('current', 0)))
                row_parts.append(str(sensor_info.get('power', 0)))
        
        # Add MCP9808 (temperature) data for each sensor in order
        for sensor_name in sorted(SENSORS_MCP9808.keys()):
            if sensor_name in mcp9808_data:
                sensor_info = mcp9808_data[sensor_name]
                row_parts.append(str(sensor_info.get('temp_c', 0)))
        
        row_parts.append(client_time)
        row = ', '.join(row_parts) + '\n'
        
        with open(OUTPUT_FILE, 'a') as f:
            f.write(row)
            f.flush()
            os.fsync(f.fileno())
        
        # Print summary
        print(f"[SERVER TIME] {timestamp}", end="")
        # Print INA260 data
        for sensor_name in sorted(SENSORS_INA260.keys()):
            if sensor_name in ina260_data:
                info = ina260_data[sensor_name]
                print(f" | {sensor_name}:V{info.get('voltage', 0)}V,I{info.get('current', 0)}mA,P{info.get('power', 0)}mW", end="")
        # Print MCP9808 data
        for sensor_name in sorted(SENSORS_MCP9808.keys()):
            if sensor_name in mcp9808_data:
                info = mcp9808_data[sensor_name]
                print(f" | {sensor_name}:T{info.get('temp_c', 0)}C", end="")
        print()
    except Exception as e:
        print(f"Error saving data: {e}")

def start_server():
    """
    Start TCP server to receive and save sensor data.
    Server provides timestamp (time authority) for all clients.
    """
    initialize_output_file()
    
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_LISTEN_IP, SERVER_PORT))
    server_socket.listen(5)
    
    if DEBUG:
        print(f"[SERVER] Configuration loaded from config.py")
    
    print(f"TIME AUTHORITY SERVER listening on {SERVER_LISTEN_IP}:{SERVER_PORT}")
    print(f"[SERVER] Output file: {OUTPUT_FILE}")
    print(f"[SERVER] Note: Server saves all received data (sampling controlled by client)")
    print("Waiting for data from client...")
    
    data_received_count = 0
    
    try:
        while True:
            # Accept incoming connection
            client_socket, client_address = server_socket.accept()
            print(f"\nConnection from {client_address}")
            
            try:
                # Receive data from client
                data_buffer = b""
                while True:
                    chunk = client_socket.recv(1024)
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
                                
                                # Send server timestamp back to client for synchronization
                                response = json.dumps({'timestamp': server_timestamp}) + '\n'
                                client_socket.sendall(response.encode('utf-8'))
                                
                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON: {e}")
                        break
            finally:
                client_socket.close()
                
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()
        print("Server closed")

if __name__ == "__main__":
    start_server()
