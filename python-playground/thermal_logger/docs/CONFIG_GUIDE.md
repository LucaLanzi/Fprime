# Configuration Guide

This system uses separate configuration files for each component, allowing independent customization of the server, IMX8 client, and Jetson client.

## Configuration Files

### Server Configuration: `config_server.py`

Used by `receiver.py` - the central data collection server.

**Key Settings:**

```python
# Network
SERVER_LISTEN_IP = "0.0.0.0"      # Listen on all interfaces (allow remote)
SERVER_PORT = 8000                 # Port for clients to connect

# Output
SERVER_OUTPUT_FILE = "received_data.csv"  # Archive file for all clients

# Debug
DEBUG = True                       # Verbose logging
SOCKET_BUFFER_SIZE = 1024         # Data buffer size (bytes)
SOCKET_TIMEOUT = 5                # Client connection timeout (seconds)
```

**When to modify:**

- Change `SERVER_LISTEN_IP` to `"127.0.0.1"` for local-only testing
- Increase `SOCKET_TIMEOUT` if clients are on slow networks
- Adjust `SOCKET_BUFFER_SIZE` if sending large data packets

---

### IMX8 Client Configuration: `config_imx8.py`

Used by `imx8x_logger.py` - reads power and temperature sensors from IMX8 device.

**Key Settings:**

```python
# Network
SERVER_IP = "127.0.0.1"           # Server address (change for network)
SERVER_PORT = 8000                 # Must match server's SERVER_PORT
CLIENT_DEVICE_ID = "imx8"         # Device name in CSV output

# Sensors
I2C_BUS = 1                        # I2C bus number
SENSORS_INA260 = {...}            # Power sensor addresses (3x)
SENSORS_MCP9808 = {...}           # Thermal sensor addresses (3x)

# Sampling
NUM_READINGS = 20                  # How many samples to take
READ_INTERVAL = 0.1               # Seconds between readings
SAVE_EVERY = 1                    # Save every Nth reading
NUM_READINGS * READ_INTERVAL → 2 seconds data with SAVE_EVERY=1

# Hardware
SIMULATE_SENSOR = True            # Use synthetic data (False for real)
```

**Configuration Examples:**

**Local testing (simulated data):**
```python
SERVER_IP = "127.0.0.1"
SIMULATE_SENSOR = True
```

**Network deployment (real sensors):**
```python
SERVER_IP = "192.168.1.100"       # Server's actual IP
SIMULATE_SENSOR = False           # Read actual I2C sensors
SAVE_EVERY = 5                    # Save every 5th sample (less data)
```

**High-frequency sampling:**
```python
READ_INTERVAL = 0.01              # Sample 100x per second
SAVE_EVERY = 1                    # Save all readings
```

**Low-bandwidth sampling:**
```python
READ_INTERVAL = 0.1               # Sample 10x per second
SAVE_EVERY = 10                   # Save every 10 samples (1x per second)
NUM_READINGS = 600                # 1 minute at this rate
```

---

### Jetson Client Configuration: `config_jetson.py`

Used by `jetson_logger.py` - reads thermal zones from Jetson Orin AGX.

**Key Settings:**

```python
# Network
JETSON_SERVER_IP = "127.0.0.1"
JETSON_SERVER_PORT = 8000
JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"

# Sampling
JETSON_NUM_READINGS = 20          # Samples to take
JETSON_READ_INTERVAL = 0.1        # Seconds between readings
JETSON_SAVE_EVERY = 1             # Save every Nth reading

# Hardware
MAX_THERMAL_ZONES = 10            # Max zones to log (0-9)
JETSON_THERMAL_ZONE_PATHS = [...]  # Kernel thermal zone files
SIMULATE_SENSOR = True            # Use synthetic data
```

**Configuration Examples:**

**Local testing (simulated):**
```python
JETSON_SERVER_IP = "127.0.0.1"
SIMULATE_SENSOR = True
```

**Network deployment (real thermal zones):**
```python
JETSON_SERVER_IP = "192.168.1.100"
SIMULATE_SENSOR = False
JETSON_SAVE_EVERY = 2             # Save every 2nd reading
```

---

## Configuration Workflow

### Step 1: Prepare Server Machine

1. Edit `config_server.py`:
   ```python
   SERVER_LISTEN_IP = "0.0.0.0"    # Allow remote connections
   SERVER_PORT = 8000
   DEBUG = True
   ```

2. Note the server's IP address:
   ```bash
   # Find server IP
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

### Step 2: Configure IMX8 Client

1. On IMX8 device, edit `config_imx8.py`:
   ```python
   SERVER_IP = "192.168.1.100"     # Server's IP from Step 1
   SERVER_PORT = 8000              # Same as server
   NUM_READINGS = 20               # How many samples
   READ_INTERVAL = 0.1             # Interval between samples
   SAVE_EVERY = 1                  # Save every sample
   SIMULATE_SENSOR = False         # For real hardware
   ```

### Step 3: Configure Jetson Client

1. On Jetson device, edit `config_jetson.py`:
   ```python
   JETSON_SERVER_IP = "192.168.1.100"   # Server's IP
   JETSON_SERVER_PORT = 8000
   JETSON_NUM_READINGS = 20
   JETSON_READ_INTERVAL = 0.1
   JETSON_SAVE_EVERY = 1
   SIMULATE_SENSOR = False
   ```

### Step 4: Run All Components

**On Server Machine:**
```bash
python3 receiver.py
# Output: TIME AUTHORITY SERVER listening on 0.0.0.0:8000
```

**On IMX8 Machine:**
```bash
python3 imx8x_logger.py
# Sends data to server
```

**On Jetson Machine:**
```bash
python3 jetson_logger.py
# Sends data to server
```

---

## Sampling & Data Rate Control

### Understanding SAVE_EVERY

```
READ_INTERVAL = 0.1 seconds (10 samples/second)
SAVE_EVERY = 5

Result: Save every 5th sample = 2 samples/second to disk
```

**Use Cases:**

| SAVE_EVERY | Disk Rate | File Size (1 hour) | Use Case |
|-----------|-----------|------------------|----------|
| 1 | 10 Hz | ~450 KB | High fidelity (default) |
| 5 | 2 Hz | ~90 KB | Normal monitoring |
| 10 | 1 Hz | ~45 KB | Low bandwidth networks |
| 50 | 0.2 Hz | ~9 KB | Ultra-low data |

**Network Bandwidth Estimate:**

Each packet ≈ 500 bytes (varies by sensor count)
- SAVE_EVERY=1, 10Hz: ~5 KB/second = 18 MB/hour
- SAVE_EVERY=10, 1Hz: ~0.5 KB/second = 1.8 MB/hour

---

## Troubleshooting Configuration

**"Connection refused" error:**
- Check `config_imx8.py` or `config_jetson.py` has correct `SERVER_IP`
- Verify `SERVER_PORT` matches `config_server.py`
- Ensure server is running: `python3 receiver.py`

**"ModuleNotFoundError: No module named 'config_server'":**
- Ensure `config_server.py`, `config_imx8.py`, `config_jetson.py` are in same directory
- Check filename capitalization (must be lowercase with underscore)

**Data not saving to CSV:**
- Check `SIMULATE_SENSOR` setting matches your hardware
- Verify I2C devices are connected (for IMX8)
- Check thermal zone files exist (for Jetson):
  ```bash
  ls /sys/class/thermal/thermal_zone0/temp
  ```

**Network timeouts:**
- Increase `SOCKET_TIMEOUT` in `config_server.py`
- Increase `NETWORK_TIMEOUT` in `config_imx8.py` or `config_jetson.py`
- Check network connectivity:
  ```bash
  ping serverip
  ```

---

## Quick Reference

### Common Configurations

**Development (local, simulated):**
```python
# config_server.py
SERVER_LISTEN_IP = "127.0.0.1"

# config_imx8.py
SERVER_IP = "127.0.0.1"
SIMULATE_SENSOR = True
NUM_READINGS = 10
SAVE_EVERY = 1

# config_jetson.py
JETSON_SERVER_IP = "127.0.0.1"
SIMULATE_SENSOR = True
JETSON_NUM_READINGS = 10
JETSON_SAVE_EVERY = 1
```

**Production (network, real hardware):**
```python
# config_server.py
SERVER_LISTEN_IP = "0.0.0.0"
DEBUG = False

# config_imx8.py
SERVER_IP = "192.168.1.100"
SIMULATE_SENSOR = False
NUM_READINGS = 3600           # 1 hour @ 0.1s interval
SAVE_EVERY = 10               # 1 Hz save rate

# config_jetson.py
JETSON_SERVER_IP = "192.168.1.100"
SIMULATE_SENSOR = False
JETSON_NUM_READINGS = 3600
JETSON_SAVE_EVERY = 10
```

**Long-term monitoring (very low bandwidth):**
```python
# config_imx8.py
NUM_READINGS = 36000          # 1 hour
READ_INTERVAL = 0.1
SAVE_EVERY = 100              # Save every 10 seconds

# config_jetson.py
JETSON_NUM_READINGS = 36000
JETSON_READ_INTERVAL = 0.1
JETSON_SAVE_EVERY = 100
```

---

## Configuration Validation

Before running, verify your config files are correct:

```bash
# Check Python syntax
python3 -m py_compile config_server.py config_imx8.py config_jetson.py

# Run in test mode (with SIMULATE_SENSOR = True first)
python3 receiver.py  # In one terminal

# In another terminal
python3 imx8x_logger.py

# In third terminal  
python3 jetson_logger.py
```

All three should run without errors. Check console output for:
- `[SERVER] Configuration loaded`
- `[CLIENT] Using synthetic sensor data` (if SIMULATE_SENSOR=True)
- Data rows in received_data.csv

Once verified with simulation, set `SIMULATE_SENSOR = False` for real data.
