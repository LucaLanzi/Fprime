"""
Configuration file for Jetson Orin AGX thermal logger client.
Customize these settings for your Jetson device and network.
"""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

# Server IP address
# For LOCAL TESTING: "127.0.0.1" or "localhost"
# For NETWORK TESTING: Use the server's actual IP (e.g., "192.168.1.100")
JETSON_SERVER_IP = "127.0.0.1"

# Server port (must match receiver.py SERVER_PORT)
JETSON_SERVER_PORT = 8000

# Client device identifier (used to identify this device in CSV files)
JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"

# ============================================================================
# DATA COLLECTION CONFIGURATION
# ============================================================================

# Number of readings to take
JETSON_NUM_READINGS = 20

# Delay between readings (in seconds)
JETSON_READ_INTERVAL = 0.1

# SAMPLING CONTROL: Save every Nth reading (decimation)
# Examples:
#   SAVE_EVERY = 1   → Save all readings (no decimation)
#   SAVE_EVERY = 5   → Save every 5th reading
#   SAVE_EVERY = 10  → Save every 10th reading
JETSON_SAVE_EVERY = 1

# Local output file for thermal data (Jetson client-side)
JETSON_OUTPUT_FILE = "logs/jetson_logs.csv"

# ============================================================================
# JETSON THERMAL ZONE CONFIGURATION
# ============================================================================

# Jetson thermal zone paths
# The Jetson Orin AGX typically has multiple thermal zones:
# zone 0: GPU temperature
# zone 1: System temperature (CPU, memory, etc.)
# zone 2: AO (Always On) domains temperature
# zone 3: PLLX temperature
# etc.
JETSON_THERMAL_ZONE_PATHS = [
    "/sys/class/thermal/thermal_zone0/temp",  # GPU
    "/sys/class/thermal/thermal_zone1/temp",  # System
    "/sys/class/thermal/thermal_zone2/temp",  # AO
    "/sys/class/thermal/thermal_zone3/temp",  # PLLX
    "/sys/class/thermal/thermal_zone4/temp",  # CVNAS
    "/sys/class/thermal/thermal_zone5/temp",  # Thermal throttle
    "/sys/class/thermal/thermal_zone6/temp",  # TJ_MAX
    "/sys/class/thermal/thermal_zone7/temp",  # Additional zones
    "/sys/class/thermal/thermal_zone8/temp",
    "/sys/class/thermal/thermal_zone9/temp",
]

# Maximum number of thermal zones to log
MAX_THERMAL_ZONES = 10

# ============================================================================
# DEBUG / DEVELOPMENT
# ============================================================================

# Enable debug printing for Jetson client
DEBUG = True

# Simulate sensor data if hardware thermal sensors not available
SIMULATE_SENSOR = True

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
