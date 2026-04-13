"""
Configuration file for INA260 sensor data collection and synchronization.
Modify these settings to match your environment.
"""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

# Server IP address
# For LOCAL TESTING: "127.0.0.1" or "localhost"
# For NETWORK TESTING: Use the server's actual IP (e.g., "192.168.1.100")
SERVER_IP = "127.0.0.1"

# Server port
SERVER_PORT = 8000

# ============================================================================
# SENSOR CONFIGURATION (INA260)
# ============================================================================

# I2C bus number
# Raspberry Pi typically uses: 1
# Some systems use: 0
I2C_BUS = 1

# INA260 Sensors - Define all sensors with their I2C addresses and names
# Format: {name: {address: 0xXX, description: "..."}}
SENSORS_INA260 = {
    'obc': {
        'address': 0x41,
        'description': 'Onboard Computer Switching Regulator'
    },
    'perif': {
        'address': 0x45,
        'description': 'Peripheral System Switching Regulator'
    },
    'jetson': {
        'address': 0x40,
        'description': 'Jetson Switching Regulator'
    }
}

# MCP9808 Temperature Sensors - Define all temperature sensors
# Format: {name: {address: 0xXX, description: "..."}}
SENSORS_MCP9808 = {
    'obc': {
        'address': 0x19,
        'description': 'Onboard Computer Temperature'
    },
    'perif': {
        'address': 0x1A,
        'description': 'Peripheral System Temperature'
    },
    'jetson': {
        'address': 0x1B,
        'description': 'Jetson Temperature'
    }
}

# For backward compatibility
SENSORS = SENSORS_INA260

# INA260 Register addresses (read-only after device initialization)
INA260_CONFIG = 0x00
INA260_CURRENT = 0x01
INA260_BUS_VOLTAGE = 0x02
INA260_POWER = 0x03

# MCP9808 Register addresses
MCP9808_REG_CONFIG = 0x01
MCP9808_REG_TEMP = 0x05        # Temperature register
MCP9808_REG_TALOW = 0x02
MCP9808_REG_TAHIGH = 0x03

# ============================================================================
# CLIENT (SENSOR DEVICE) CONFIGURATION
# ============================================================================

# Number of readings to take
NUM_READINGS = 20

# Delay between readings (in seconds)
READ_INTERVAL = 0.1

# SAMPLING CONTROL: Save every Nth reading (decimation)
# Examples:
#   SAVE_EVERY = 1   → Save all readings (no decimation)
#   SAVE_EVERY = 5   → Save every 5th reading (read 5x more often than save)
#   SAVE_EVERY = 10  → Save every 10th reading
SAVE_EVERY = 1

# Local output file for sensor data (client-side)
CLIENT_OUTPUT_FILE = "logs/logs.csv"

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Server listen address (0.0.0.0 = listen on all interfaces)
SERVER_LISTEN_IP = "0.0.0.0"

# Server output file for archived data
SERVER_OUTPUT_FILE = "received_data.csv"

# NOTE: Server saves every reading it receives
# (Sampling is controlled by CLIENT's SAVE_EVERY setting)

# ============================================================================
# DEBUG / DEVELOPMENT
# ============================================================================

# Enable debug printing
DEBUG = True

# Simulate sensor data if I2C hardware not available
SIMULATE_SENSOR = True

# Timestamp format for data files (Excel-compatible)
# Format: YYYY-MM-DD HH:MM:SS.ffffff (space instead of T for Excel recognition)
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

# ============================================================================
# TESTING PRESETS
# ============================================================================

def load_localhost_preset():
    """Configure for local testing on same machine."""
    global SERVER_IP, NUM_READINGS, READ_INTERVAL
    SERVER_IP = "127.0.0.1"
    print("[CONFIG] Loaded LOCALHOST preset - both programs on same machine")

def load_network_preset(server_ip):
    """Configure for network testing on different machines."""
    global SERVER_IP
    SERVER_IP = server_ip
    print(f"[CONFIG] Loaded NETWORK preset - server at {server_ip}")

# Use presets if needed:
# load_localhost_preset()  # Uncomment for local testing
# load_network_preset("192.168.1.100")  # Uncomment for network testing
