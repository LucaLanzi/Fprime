# Power and Temperature Sensor Data Logger

A networked multi-device thermal and power monitoring system that reads sensors from IMX8 and Jetson devices, synchronizes timestamps across multiple machines, and logs all data exclusively to a remote receiver server.

## Quick Overview

- **IMX8 Logger** - Reads power (INA260) and temperature (MCP9808 + CPU) sensors
- **Jetson Logger** - Reads all Jetson thermal zones
- **Server (receiver.py)** - Centralized time authority, receives data from all clients, saves to device-specific CSV files
- **Remote-only logging** - All data stored exclusively on the server machine
- **Handshake protocol** - Loggers wait for server confirmation before starting data collection
- **Multi-threaded** - Handles multiple concurrent client connections

## Architecture

### Single Machine / Local Testing
```
┌──────────────────────┐          TCP/IP          ┌──────────────────────┐
│  IMX8 DEVICE         │         (Port 8000)       │  SERVER              │
│  (imx8x_logger.py)   │────────────────────────→  │  (receiver.py)       │
│  • INA260 Power      │                           │                      │
│  • MCP9808 Temp      │←──────────────────────   │  Handshake:          │
│  • IMX8 CPU Temp     │   Timestamp Response      │  {'status':'ready'}  │
└──────────────────────┘                           │                      │
                                                   │  received_data.csv   │
                                                   └──────────────────────┘
```

### Multi-Device / Network Setup
```
┌──────────────────────┐                         ┌──────────────────────┐
│  IMX8 DEVICE         │                         │  SERVER              │
│  (imx8x_logger.py)   │\                        │  (receiver.py)       │
│  • Power Sensors     │ \       TCP/IP          │                      │
│  • Temperature       │  \    (Port 8000)       │  Time Authority      │
│  • CPU Temp          │   \   (multi-device)    │  Multi-threaded      │
└──────────────────────┘    \                    │                      │
                            → ──────────────→   │  received_data_imx8.csv  │
                            ←── (handshake)      │  received_data_jetson.csv│
┌──────────────────────┐    /                    └──────────────────────┘
│  JETSON ORIN AGX     │   /
│  (jetson_logger.py)  │  /
│  • 10 Thermal Zones  │ /
│  • GPU/System/AO etc │/
└──────────────────────┘
```

## Installation & Setup

### Requirements
- Python 3.6+
- `smbus2` library (for I2C communication)

### Install Dependencies
```bash
pip install smbus2
```

## Quick Start - Local Testing (Same Machine)

**Terminal 1 - Start Server:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground/thermal_logger
python src/receiver.py
```

**Terminal 2 - Run IMX8 Logger:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground/thermal_logger
python src/imx8x_logger.py
```

**Terminal 3 (Optional) - Run Jetson Logger:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground/thermal_logger
python src/jetson_logger.py
```

### Quick Start - Network Testing (Different Machines)

**On Server Machine:**
1. Find your IP: `ifconfig | grep "inet " | grep -v 127.0.0.1`
2. Start server: `python src/receiver.py`

**On IMX8 Sensor Machine:**
1. Edit `config/config_imx8.py`:
   ```python
   SERVER_IP = "192.168.1.100"  # Server's actual IP
   ```
2. Run: `python src/imx8x_logger.py`

**On Jetson Sensor Machine:**
1. Edit `config/config_jetson.py`:
   ```python
   JETSON_SERVER_IP = "192.168.1.100"  # Server's actual IP
   ```
2. Run: `python src/jetson_logger.py`

## Configuration

### Key Settings

| File | Setting | Default | Description |
|------|---------|---------|-------------|
| config_imx8.py | `SERVER_IP` | `"127.0.0.1"` | Server address (localhost or remote IP) |
| config_imx8.py | `CLIENT_DEVICE_ID` | `"imx8"` | Device identifier in CSV |
| config_imx8.py | `SEND_FREQUENCY_HZ` | `1.0` | **Times per second to send data** |
| config_imx8.py | `READ_INTERVAL` | `0.5` | Seconds between sensor reads |
| config_jetson.py | `JETSON_SERVER_IP` | `"127.0.0.1"` | Server address |
| config_jetson.py | `JETSON_CLIENT_DEVICE_ID` | `"jetson_orin_agx"` | Device identifier |
| config_jetson.py | `JETSON_SEND_FREQUENCY_HZ` | `1.0` | **Times per second to send data** |
| config_jetson.py | `JETSON_READ_INTERVAL` | `0.1` | Seconds between thermal zone reads |
| config_server.py | `SERVER_PORT` | `8000` | Network port |
| all | `SIMULATE_SENSOR` | `False` (imx8), `True` (jetson) | Use synthetic data for testing |

### Send Frequency (Times Per Second)

Control how often data is sent to the receiver:

```python
# 1 Hz - Send once per second (DEFAULT)
SEND_FREQUENCY_HZ = 1.0

# 10 Hz - Send 10 times per second (more network traffic)
SEND_FREQUENCY_HZ = 10.0

# 0.5 Hz - Send once every 2 seconds (less network traffic)
SEND_FREQUENCY_HZ = 0.5
```

### Sensor Configuration

**IMX8 Power Sensors (INA260):**
```python
SENSORS_INA260 = {
    'obc': {'address': 0x41, 'description': 'Onboard Computer Switching Regulator'},
    'perif': {'address': 0x45, 'description': 'Peripheral System Switching Regulator'},
    'jetson': {'address': 0x40, 'description': 'Jetson Switching Regulator'}
}
```

**IMX8 Temperature Sensors (MCP9808):**
```python
SENSORS_MCP9808 = {
    'obc': {'address': 0x19, 'description': 'Onboard Computer Temperature'},
    'perif': {'address': 0x1A, 'description': 'Peripheral System Temperature'},
    'jetson': {'address': 0x1B, 'description': 'Jetson Temperature'}
}
```

**Jetson Thermal Zones:**
```python
JETSON_THERMAL_ZONE_PATHS = [
    "/sys/class/thermal/thermal_zone0/temp",  # GPU
    "/sys/class/thermal/thermal_zone1/temp",  # System
    "/sys/class/thermal/thermal_zone2/temp",  # AO (Always-On)
    # ... additional zones up to 10
]
```

## Sensors

### IMX8 Device
- **3x INA260 Power Monitors**: OBC (0x41), Perif (0x45), Jetson (0x40)
  - Reads: Voltage, Current, Power
- **3x MCP9808 Temperature**: OBC (0x19), Perif (0x1A), Jetson (0x1B)
  - Reads: Temperature
- **1x IMX8 CPU Temp**: Linux thermal zone
  - Reads: SOC CPU temperature

### Jetson Device
- **10 Thermal Zones**: GPU, System, AO, PLLX, CVNAS, and more
  - Reads: Temperature

## Data Flow & Logging

### Architecture Changes (Remote-Only Logging)

**Before:** Data logged on both logger machines and server (duplicate)
**Now:** Data logged ONLY on server (single source of truth)

### How It Works

1. **Logger starts** → Waits for server connection
2. **Server sends handshake** → `{"status": "ready"}`
3. **Logger confirms handshake** → Starts reading sensors
4. **Logger sends data** → At configured frequency (Hz)
5. **Server stores data** → In device-specific CSV files

### CSV Output Files

Server creates **separate files per device**:
- `received_data_imx8.csv` - IMX8 sensor data
- `received_data_jetson.csv` - Jetson thermal data

**Example received_data_imx8.csv:**
```
server_timestamp,jetson_voltage_V,jetson_current_mA,jetson_power_mW,obc_voltage_V,obc_current_mA,obc_power_mW,perif_voltage_V,perif_current_mA,perif_power_mW,jetson_temp_C,obc_temp_C,perif_temp_C,imx8_cpu_temp_C,client_time
2026-04-13 12:05:40.986311,5.075,292.44,1998.2,5.152,219.29,1936.5,5.165,228.28,1851.9,55.03,32.49,21.37,58.49,2026-04-13 12:05:40.985867
2026-04-13 12:05:41.986311,5.080,293.10,2001.5,5.155,220.12,1940.8,5.170,229.05,1855.2,55.12,32.56,21.42,58.52,2026-04-13 12:05:41.985867
```

**Example received_data_jetson.csv:**
```
server_timestamp,jetson_thermal_zone0_C,jetson_thermal_zone1_C,jetson_thermal_zone2_C,jetson_thermal_zone3_C,jetson_thermal_zone4_C,jetson_thermal_zone5_C,jetson_thermal_zone6_C,jetson_thermal_zone7_C,jetson_thermal_zone8_C,jetson_thermal_zone9_C,client_time
2026-04-13 12:05:43.713826,59.09,68.92,43.07,41.19,53.21,35.38,41.1,35.58,42.54,56.56,2026-04-13 12:05:43.713565
2026-04-13 12:05:44.713826,59.15,69.01,43.12,41.23,53.28,35.42,41.15,35.62,42.61,56.62,2026-04-13 12:05:44.713565
```

### CSV Columns Explained

| Column | Description |
|--------|-------------|
| `server_timestamp` | Authoritative time from server (Excel datetime) |
| `jetson_voltage_V`, `obc_voltage_V`, `perif_voltage_V` | Voltage in volts (INA260) |
| `*_current_mA` | Current in milliamps (INA260) |
| `*_power_mW` | Power in milliwatts (INA260) |
| `*_temp_C` | Temperature in Celsius |
| `jetson_thermal_zone*_C` | Jetson thermal zone (10 zones) |
| `client_time` | Time from logger device (for diagnosing clock issues) |

## System Features

✅ **Remote-Only Logging** - Data exclusively on server  
✅ **Server Handshake** - Loggers wait for confirmation  
✅ **Frequency Control** - Easily adjust sends per second  
✅ **Multi-Device Support** - Handle multiple loggers simultaneously  
✅ **Time Authority** - Server provides authoritative timestamps  
✅ **Excel Compatible** - Direct import and charting  
✅ **Simulation Mode** - Test without hardware  
✅ **Multi-Threaded** - Concurrent client handling  

## Project Structure

```
thermal_logger/
├── README.md                 # This file
├── config/
│   ├── config_imx8.py       # IMX8 logger settings
│   ├── config_jetson.py     # Jetson logger settings
│   └── config_server.py     # Server settings
├── src/
│   ├── imx8x_logger.py      # IMX8 sensor reader
│   ├── jetson_logger.py     # Jetson thermal reader
│   └── receiver.py          # Centralized server
└── logs/                     # Output directory (created at runtime)
```

## Troubleshooting

### "Connection refused" - Can't Connect to Server

**Check:**
1. Is `receiver.py` running on the server? (`ps aux | grep receiver.py`)
2. Is `SERVER_IP` correct in config? (for local: `127.0.0.1`, for network: actual IP)
3. Can you ping the server? (`ping 192.168.1.100`)
4. Is firewall blocking port 8000?

### "ModuleNotFoundError: No module named 'smbus2'"

```bash
pip install smbus2
```

### "Error reading INA260" / "Error reading MCP9808"

**Check:**
1. Are sensors connected to correct I2C pins?
2. Are I2C addresses correct? Use: `i2cdetect -y 1`
3. Is `I2C_BUS` correct in config? (usually `1` for Raspberry Pi)
4. Set `SIMULATE_SENSOR = True` to test without hardware

### Timestamps Don't Match Between Devices

Server time is authoritative. Sync all devices to server's clock:

```bash
# Linux/Raspberry Pi
sudo ntpdate -s time.nist.gov

# macOS
sudo sntp -sS time.apple.com
```

### Excel Can't Parse Timestamps

Verify timestamp format in all config files:
```python
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"  # Space between date/time (not T)
```

## Testing

### Test with Simulation Mode (No Hardware Required)

```python
# config/config_imx8.py and config/config_jetson.py
SIMULATE_SENSOR = True
```

Generates realistic synthetic data for testing network, logging, and CSV output.

### Test Connection & Handshake

```bash
# Terminal 1
python src/receiver.py

# Terminal 2 (should show handshake received)
DEBUG = True  # Enable in config
python src/imx8x_logger.py
```

Look for: `Server handshake received! Server is ready!`

## Advanced Features

### Multiple Simultaneous Clients

The server handles multiple loggers concurrently. Each device gets its own CSV file:

```
received_data_imx8.csv
received_data_jetson.csv
received_data_other_device.csv
```

### Rate Limiting Examples

```python
# Slow polling (bandwidth-limited environments)
SEND_FREQUENCY_HZ = 0.1  # 1 send every 10 seconds

# Standard monitoring (default)
SEND_FREQUENCY_HZ = 1.0  # 1 send per second

# Real-time monitoring
SEND_FREQUENCY_HZ = 10.0  # 10 sends per second

# High-frequency capture
SEND_FREQUENCY_HZ = 50.0  # 50 sends per second
```

## References

- **INA260** - Power Monitor (I2C address configurable 0x40-0x4F)
- **MCP9808** - Temperature Sensor (I2C address configurable 0x18-0x1F)
- **Jetson Orin AGX** - Thermal zones exposed at `/sys/class/thermal/thermal_zone*/temp`

## License

See LICENSE file in repository.

---

**For more details on specific components, configuration options, or multi-device setup, see the configuration files in `config/` directory.**
