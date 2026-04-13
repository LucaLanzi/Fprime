# Multi-Device Temperature Logger System

This system allows multiple devices (IMX8, Jetson, etc.) to send thermal and power readings to a central receiver server, which logs all data to a single CSV file for combined analysis and plotting.

## Architecture

- **receiver.py**: Central server that listens on port 8000 (multi-threaded, handles multiple concurrent clients)
- **imx8x_logger.py**: Client for IMX8 SoC devices - reads CPU temperature from Linux thermal zones
- **jetson_logger.py**: Client for NVIDIA Jetson Orin AGX - reads all thermal zones from the device

## Quick Start

### 1. Start the Receiver Server (on main machine)

```bash
python3 receiver.py
```

You should see:
```
TIME AUTHORITY SERVER listening on 0.0.0.0:8000
[SERVER] Output file: received_data.csv
[SERVER] Multi-threaded server - handles multiple simultaneous clients
Waiting for data from clients...
```

### 2. Start Client(s) on Your Device(s)

**On IMX8 device:**
```bash
# Edit config.py: Change SERVER_IP to receiver's IP address
SERVER_IP = "192.168.1.100"  # Change to your receiver's IP

# Run the client
python3 imx8x_logger.py
```

**On Jetson device:**
```bash
# Edit jetson_logger.py: Change JETSON_SERVER_IP to receiver's IP address
JETSON_SERVER_IP = "192.168.1.100"  # Change to your receiver's IP

# Run the client
python3 jetson_logger.py
```

## Configuration

### For IMX8 Client (imx8x_logger.py)

Edit `config.py`:
```python
SERVER_IP = "192.168.1.100"      # Receiver's IP address
SERVER_PORT = 8000                # Receiver's port
CLIENT_DEVICE_ID = "imx8"         # Device identifier in CSV
SIMULATE_SENSOR = False           # Set to False for real sensors
```

### For Jetson Client (jetson_logger.py)

Edit `jetson_logger.py` (top of file):
```python
JETSON_SERVER_IP = "192.168.1.100"      # Receiver's IP address
JETSON_SERVER_PORT = 8000                # Receiver's port
JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"
SIMULATE_SENSOR = False                  # Set to False for real sensors
```

## CSV Output Format

The receiver creates `received_data.csv` with columns:

```
server_timestamp, device_id, 
obc_voltage_V, obc_current_mA, obc_power_mW,
perif_voltage_V, perif_current_mA, perif_power_mW,
jetson_voltage_V, jetson_current_mA, jetson_power_mW,
obc_temp_C, perif_temp_C, jetson_temp_C,
imx8_cpu_temp_C,
jetson_thermal_zone0_C, jetson_thermal_zone1_C, ..., jetson_thermal_zone9_C,
client_time
```

### Example CSV Entries

```csv
2026-04-13 12:30:45.123456,imx8,,,,,,,,,,,45.2,,,,,,,,,,,client_time
2026-04-13 12:30:45.234567,jetson_orin_agx,,,,,,,,,,,,72.1,65.3,58.2,48.1,52.3,55.1
```

- **IMX8 row**: Shows IMX8 CPU temp (45.2°C), blank columns for Jetson thermal zones
- **Jetson row**: Shows all thermal zones (GPU: 72.1°C, System: 65.3°C, etc.)

## Data Structure Sent Over Network

Each client sends JSON data:

```json
{
  "device_id": "imx8",
  "sensors": {
    "ina260": {"obc": {"voltage": 5.0, "current": 350, "power": 1750}},
    "mcp9808": {"obc": {"temp_c": 35.5}},
    "imx8": {"temp_c": 45.2}
  },
  "client_time": "2026-04-13 12:30:45.123456"
}
```

For Jetson:
```json
{
  "device_id": "jetson_orin_agx",
  "sensors": {
    "jetson_thermal": {
      "zone_0": 72.1,
      "zone_1": 65.3,
      "zone_2": 58.2
    }
  },
  "client_time": "2026-04-13 12:30:45.234567"
}
```

## Thread Safety

The receiver uses a `file_lock` (threading.Lock) to ensure thread-safe CSV writes when multiple clients connect simultaneously. This prevents data corruption from concurrent writes.

## Plotting Combined Data

You can now plot temperature data from both devices using pandas/matplotlib:

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('received_data.csv')

# Plot IMX8 CPU temperature
imx8_data = df[df['device_id'] == 'imx8']
plt.plot(imx8_data.index, imx8_data['imx8_cpu_temp_C'], label='IMX8 CPU')

# Plot Jetson GPU temperature
jetson_data = df[df['device_id'] == 'jetson_orin_agx']
plt.plot(jetson_data.index, jetson_data['jetson_thermal_zone0_C'], label='Jetson GPU')

plt.xlabel('Sample')
plt.ylabel('Temperature (°C)')
plt.legend()
plt.show()
```

## Jetson Thermal Zones Reference

The Jetson Orin AGX typically has these thermal zones:

- **Zone 0**: GPU temperature (high-performance)
- **Zone 1**: System temperature (CPU, memory, cache)
- **Zone 2**: AO (Always-On) domains
- **Zone 3**: PLLX voltage regulator
- **Zone 4**: CVNAS (Cluster Voltage and Noise Avoidance System)
- **Zone 5**: Thermal throttle monitoring
- **Zone 6**: TJ_MAX (maximum junction temperature)
- **Zones 7-9**: Additional thermal monitoring domains (varies by firmware)

You can verify which zones are available on your Jetson:
```bash
ls -la /sys/class/thermal/thermal_zone*/temp
```

## Troubleshooting

### "Connection refused" Error
- Ensure receiver.py is running on the server machine
- Check the IP address matches the receiver's actual IP
- Ensure port 8000 is not blocked by firewall

### No thermal data from Jetson
- Verify thermal zone files exist: `cat /sys/class/thermal/thermal_zone0/temp`
- Check permissions (may need sudo)
- Disable SIMULATE_SENSOR to read actual values vs. random data

### CSV has empty columns for client data
- This is intentional - each client only populates its own columns
- IMX8 leaves Jetson thermal zones empty, and vice versa
- This allows easy combination and plotting in analysis tools

## Running Multiple Clients on Same Device

You can run multiple client instances locally for testing:

```bash
# Terminal 1: Receiver
python3 receiver.py

# Terminal 2: IMX8 client (localhost)
python3 imx8x_logger.py

# Terminal 3: Jetson client (localhost)
python3 jetson_logger.py
```

Both will send to the same receiver and appear in the CSV with different `device_id` values.

## Local Logging

Both clients also create timestamped local CSV files in the `logs/` directory for backup/debugging:
- `logs/logs_YYYY-MM-DD_HH-MM-SS.csv` (IMX8)
- `logs/jetson_logs_YYYY-MM-DD_HH-MM-SS.csv` (Jetson)

These are optional and can be disabled by editing the `appender_local()` calls.
