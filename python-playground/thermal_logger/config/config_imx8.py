"""
Configuration file for IMX8 sensor logger client.
Customize these settings for your IMX8 device and network.
"""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

# Server IP address
# For LOCAL TESTING: "127.0.0.1" or "localhost"
# For NETWORK TESTING: Use the server's actual IP (e.g., "192.168.1.100")
SERVER_IP = "192.168.3.13"

# Server port (must match receiver.py SERVER_PORT)
SERVER_PORT = 8000

# Client device identifier (used to identify this device in CSV files)
CLIENT_DEVICE_ID = "imx8"

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
# IMX8 SoC CPU TEMPERATURE CONFIGURATION
# ============================================================================

# IMX8 CPU temperature sensor path (reads system CPU temperature)
# The kernel exports thermal zone files at /sys/class/thermal/thermal_zoneX/
# thermal_zone0 typically contains the CPU die temperature
# Values are in millidegrees Celsius (divide by 1000 to get °C)
IMX8_TEMP_SENSOR_PATH = "/sys/class/thermal/thermal_zone0/temp"

# Fallback paths if the primary path doesn't exist
IMX8_TEMP_SENSOR_FALLBACK_PATHS = [
    "/sys/devices/virtual/thermal/thermal_zone0/temp",
    "/sys/class/thermal/thermal_zone1/temp",
    "/sys/devices/virtual/thermal/thermal_zone1/temp",
]

# ============================================================================
# DATA COLLECTION CONFIGURATION
# ============================================================================

# Number of readings to take
NUM_READINGS = 5

# Delay between readings (in seconds)
READ_INTERVAL = 0.5

# SAMPLING CONTROL: Save every Nth reading (decimation)
# Examples:
#   SAVE_EVERY = 1   → Save all readings (no decimation)
#   SAVE_EVERY = 5   → Save every 5th reading (read 5x more often than save)
#   SAVE_EVERY = 10  → Save every 10th reading
SAVE_EVERY = 1

# Local output file for sensor data (IMX8 client-side)
CLIENT_OUTPUT_FILE = "logs/imx_logs.csv"

# ============================================================================
# DEBUG / DEVELOPMENT
# ============================================================================

# Enable debug printing
DEBUG = True

# Simulate sensor data if I2C hardware not available
SIMULATE_SENSOR = False

# Timestamp format for data files (Excel-compatible)
# Format: YYYY-MM-DD HH:MM:SS.ffffff (space instead of T for Excel recognition)
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

# ============================================================================
# NETWORK TIMEOUT CONFIGURATION
# ============================================================================

# Socket timeout for network communication (seconds)
NETWORK_TIMEOUT = 2

# Retry attempts if connection fails
NETWORK_RETRY_ATTEMPTS = 1
