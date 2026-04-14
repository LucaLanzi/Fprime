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
# SERVER OUTPUT CONFIGURATION
# ============================================================================

# Output file for archived data from all clients
SERVER_OUTPUT_FILE = "received_data.csv"

# ============================================================================
# DEBUG / DEVELOPMENT
# ============================================================================

# Enable debug printing for server operations
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
#making a change