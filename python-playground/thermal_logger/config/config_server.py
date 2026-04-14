"""
Configuration file for the multi-device sensor data receiver server.
Customize these settings for your server environment.
"""

# ============================================================================
# SERVER NETWORK CONFIGURATION
# ============================================================================

# Server listen address
# "0.0.0.0" = listen on all interfaces (allows remote connections)
# "127.0.0.1" = localhost only (local testing only)
SERVER_LISTEN_IP = "0.0.0.0"

# Server port
# Clients must connect to this same port
SERVER_PORT = 8000

# ============================================================================
# SERVER HANDSHAKE CONFIGURATION
# ============================================================================
#
# Handshake Protocol:
# 1. Client connects to server
# 2. Server immediately sends: {"status": "ready", "message": "Server ready to receive data"}
# 3. Client receives and validates handshake
# 4. Client begins reading sensors and sending data
# 5. Server performs time synchronization and validates data
# 6. Data is logged to device-specific CSV files on server machine only
#

# ============================================================================
# SERVER OUTPUT CONFIGURATION
# ============================================================================
# 
# Server receives data from multiple clients (IMX8, Jetson, etc.)
# and creates device-specific CSV files with server-side timestamps.
# Each device's data is logged to a separate file: received_data_<device_id>.csv
#

# Output file base name (device_id will be appended: received_data_<device_id>.csv)
SERVER_OUTPUT_FILE = "received_data.csv"

# ============================================================================
# SERVER LOGGING ARCHITECTURE
# ============================================================================
#
# Single Source of Truth:
# - Server is the authoritative time source (all timestamps from server)
# - Clients send data but do NOT save locally
# - All data is saved only on server machine
# - Device-specific CSV files created on first data from each device
# - Multi-threaded server handles concurrent clients
#

# ============================================================================
# DEBUG / DEVELOPMENT
# ============================================================================

# Enable debug printing for server operations (includes handshake log)
DEBUG = True

# Timestamp format for data files (Excel-compatible)
# Format: YYYY-MM-DD HH:MM:SS.ffffff (space instead of T for Excel recognition)
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

# ============================================================================
# THREADING CONFIGURATION
# ============================================================================

# Maximum number of concurrent client connections
# Python threading can handle many connections (limited by OS)
MAX_CLIENT_CONNECTIONS = 10

# Socket receive buffer size (bytes)
# Increase if sending large data packets frequently
SOCKET_BUFFER_SIZE = 1024

# Socket timeout for client connections (seconds)
# Increase if clients are slow or network is congested
SOCKET_TIMEOUT = 5
