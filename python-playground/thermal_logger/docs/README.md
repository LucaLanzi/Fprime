# Power and Temperature Sensor Data Collection System

A networked multi-device sensor data collection system that reads power monitoring data from INA260 sensors, temperature data from MCP9808 sensors, and system temperature data from IMX8 and Jetson devices, synchronizing timestamps across multiple machines.

## Overview

This system supports multiple client types:

- **IMX8 Logger** (`imx8x_logger.py`): Reads INA260 (power), MCP9808 (temperature), and IMX8 CPU temperature sensors
- **Jetson Logger** (`jetson_logger.py`): Reads all Jetson Orin AGX thermal zones (GPU, System, AO, etc.)
- **Server** (`receiver.py`): Receives data from multiple simultaneous clients, acts as time authority, and archives to unified CSV file

Both clients save timestamped data locally. The server's clock is the authoritative time source, ensuring synchronized timestamps even if individual devices have incorrect clocks. The server uses **multi-threading** to handle multiple concurrent client connections.

> **For multi-device setup details**, see [MULTI_CLIENT_README.md](MULTI_CLIENT_README.md)

## Sensors

**INA260 Power Monitors** (3 sensors):
- **OBC** (0x41): Onboard Computer Switching Regulator - Voltage, Current, Power
- **Perif** (0x45): Peripheral System Switching Regulator - Voltage, Current, Power
- **Jetson** (0x40): Jetson Switching Regulator - Voltage, Current, Power

**MCP9808 Temperature Sensors** (3 sensors):
- **OBC** (0x19): Onboard Computer Temperature
- **Perif** (0x1A): Peripheral System Temperature
- **Jetson** (0x1B): Jetson Temperature

## System Architecture

### Single Machine / Simple Setup
```
┌─────────────────────────┐          TCP/IP          ┌──────────────────────┐
│  IMX8 DEVICE            │         (Port 8000)       │  SERVER/ARCHIVE      │
│  (imx8x_logger.py)      │────────────────────────→  │  (receiver.py)       │
│                         │                           │                      │
│  3x INA260 Sensors      │←────────────────────────  │  Time Authority      │
│  3x MCP9808 Sensors     │   Timestamp Response      │  Multi-threaded      │
│  1x IMX8 CPU Temp       │                           │  └─ received_data.csv│
│  └─ logs/logs.csv       │                           │                      │
└─────────────────────────┘                           └──────────────────────┘
```

### Multi-Device Setup (Recommended)
```
┌──────────────────────────┐                         ┌──────────────────────┐
│  IMX8 DEVICE 1           │                         │  SERVER/ARCHIVE      │
│  (imx8x_logger.py)       │                         │  (receiver.py)       │
│  • INA260 Power          │\                        │                      │
│  • MCP9808 Thermal       │ \       TCP/IP          │  Time Authority      │
│  • IMX8 CPU Temp         │  \    (Port 8000)       │  Multi-threaded      │
└──────────────────────────┘   \                     │                      │
                               → ────────────────→  │  received_data.csv   │
                               ←── (multi-threaded)  │  (all devices)       │
┌──────────────────────────┐   /                     └──────────────────────┘
│  JETSON ORIN AGX         │  /
│  (jetson_logger.py)      │ /
│  • 10x Thermal Zones     │/
│  • GPU, System, AO, etc  │
└──────────────────────────┘
```

## Installation

### Requirements

- Python 3.6+
- `smbus2` library for I2C communication

### Install Dependencies

```bash
pip install smbus2
```

Or using your virtual environment:

```bash
source fprime_playground/my_playground/fprime-venv/bin/activate
pip install smbus2
```

## Project Structure

For detailed project organization and file descriptions, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

## Documentation

📚 **Main Documentation Files:**
- [**MULTI_CLIENT_README.md**](MULTI_CLIENT_README.md) - Multi-device setup and network configuration
- [**CONFIG_GUIDE.md**](CONFIG_GUIDE.md) - Complete configuration reference for all settings
- [**PROJECT_STRUCTURE.md**](PROJECT_STRUCTURE.md) - Detailed project organization
- [**SEPARATE_CONFIG_FILES.md**](SEPARATE_CONFIG_FILES.md) - Why and how to use separate config files per device

## Configuration

### Configuration Files Structure (Updated)

Configuration has been reorganized into **device-specific files**:

- **`config/config_imx8.py`** - IMX8 client settings (SERVER_IP, I2C addresses, sensors)
- **`config/config_jetson.py`** - Jetson client settings (SERVER_IP, thermal zones)
- **`config/config_server.py`** - Server settings (LISTEN_IP, PORT, output file)

> **See [SEPARATE_CONFIG_FILES.md](SEPARATE_CONFIG_FILES.md)** for detailed explanation of why configs were separated

### Quick Configuration

**For local testing (same machine):**

```python
# config/config_imx8.py
SERVER_IP = "127.0.0.1"
CLIENT_DEVICE_ID = "imx8"

# config/config_jetson.py
JETSON_SERVER_IP = "127.0.0.1"
JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"
```

**For network testing (different machines):**

```python
# config/config_imx8.py
SERVER_IP = "192.168.1.100"  # Server machine's IP
CLIENT_DEVICE_ID = "imx8"

# config/config_jetson.py
JETSON_SERVER_IP = "192.168.1.100"  # Server machine's IP
JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"
```

### Key Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `SERVER_IP` | `127.0.0.1` | Server address (localhost or remote IP) |
| `SERVER_PORT` | `8000` | Network port for communication |
| `I2C_BUS` | `1` | I2C bus number (1 for Raspberry Pi) |
| `NUM_READINGS` | `20` | Number of sensor readings to take |
| `READ_INTERVAL` | `0.1` | Seconds between readings |
| `SAVE_EVERY` | `10` | Save every Nth reading (data reduction via decimation) |
| `SIMULATE_SENSOR` | `True` | Simulate data if no hardware available |
| `TIMESTAMP_FORMAT` | `"%Y-%m-%d %H:%M:%S.%f"` | Excel-compatible timestamp format |

### Sensor Configuration

**IMX8 - INA260 Sensors** (Power Monitoring in `config/config_imx8.py`):
```python
SENSORS_INA260 = {
    'obc': {'address': 0x41, 'description': 'Onboard Computer Switching Regulator'},
    'perif': {'address': 0x45, 'description': 'Peripheral System Switching Regulator'},
    'jetson': {'address': 0x40, 'description': 'Jetson Switching Regulator'}
}
```

**IMX8 - MCP9808 Sensors** (Temperature in `config/config_imx8.py`):
```python
SENSORS_MCP9808 = {
    'obc': {'address': 0x19, 'description': 'Onboard Computer Temperature'},
    'perif': {'address': 0x1A, 'description': 'Peripheral System Temperature'},
    'jetson': {'address': 0x1B, 'description': 'Jetson Temperature'}
}
```

**Jetson - Thermal Zones** (in `config/config_jetson.py`):
```python
JETSON_THERMAL_ZONE_PATHS = [
    "/sys/class/thermal/thermal_zone0/temp",  # GPU
    "/sys/class/thermal/thermal_zone1/temp",  # System
    "/sys/class/thermal/thermal_zone2/temp",  # AO (Always-On)
    # ... up to 10+ zones
]
```

> **For complete sensor and configuration details**, see [CONFIG_GUIDE.md](CONFIG_GUIDE.md)

## Quick Start

### Local Testing (Same Machine)

**Terminal 1 - Start the server:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground
python receiver.py
```

**Terminal 2 - Run the IMX8 client:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground
python imx8x_logger.py
```

**Terminal 3 (Optional) - Run the Jetson client:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground
python jetson_logger.py
```

Expected output:

**Server Terminal:**
```
[SERVER] Configuration loaded from config.py
TIME AUTHORITY SERVER listening on 0.0.0.0:8000
[SERVER] Output file: received_data.csv
[SERVER] Multi-threaded server - handles multiple simultaneous clients
Waiting for data from clients...

[NEW CONNECTION] from ('127.0.0.1', 54321)
[imx8] 2026-04-13 14:30:45.123456 | obc:V5.0V,I250.5mA,P1250.0mW | IMX8_CPU:T45.2C

[NEW CONNECTION] from ('127.0.0.1', 54322)
[jetson_orin_agx] 2026-04-13 14:30:45.124567 | Zone0:72.1C | Zone1:65.3C | Zone2:58.2C
```

**IMX8 Client Terminal:**
```
[CLIENT] *** SIMULATION MODE ENABLED ***
[CLIENT] Using synthetic sensor data for testing
[CLIENT] INA260 Power Sensors configured:
        - jetson    (0x40): Jetson Switching Regulator
        - obc       (0x41): Onboard Computer Switching Regulator
        - perif     (0x45): Peripheral System Switching Regulator
[CLIENT] MCP9808 Temperature Sensors configured:
        - jetson    (0x1B): Jetson Temperature
        - obc       (0x19): Onboard Computer Temperature
        - perif     (0x1A): Peripheral System Temperature

time at 1
[SKIPPED] obc:V5.0V,I250.5mA jetson:V3.3V,I150.2mA IMX8_CPU:T45.2C (buffered, not sent)
time at 2
[SYNCED] [SAVED 1] obc:V5.01V,I251.2mA jetson:V3.31V,I151.0mA IMX8_CPU:T45.3C
```

**Jetson Client Terminal:**
```
[JETSON] Connecting to server at 127.0.0.1:8000
[JETSON] Taking 20 readings
[JETSON] *** SIMULATION MODE ENABLED ***

time at 1
[SYNCED] [SAVED 1] Zone0:72.1C Zone1:65.3C Zone2:58.2C Zone3:52.1C
time at 2
[SYNCED] [SAVED 2] Zone0:72.3C Zone1:65.4C Zone2:58.1C Zone3:52.2C
```

### Network Testing (Different Machines)

> **For detailed multi-device network setup**, see [MULTI_CLIENT_README.md](MULTI_CLIENT_README.md)

**On Server Machine:**

1. Find your IP address:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Windows
   ipconfig | findstr "IPv4"
   ```

2. Start server:
   ```bash
   python receiver.py
   ```

**On IMX8 Sensor Machine:**

1. Edit `config/config_imx8.py`:
   ```python
   SERVER_IP = "192.168.1.100"  # Use your server's actual IP
   CLIENT_DEVICE_ID = "imx8"     # Device identifier
   ```

2. Run client:
   ```bash
   python src/imx8x_logger.py
   ```

**On Jetson Sensor Machine:**

1. Edit `config/config_jetson.py`:
   ```python
   JETSON_SERVER_IP = "192.168.1.100"  # Use your server's actual IP
   JETSON_CLIENT_DEVICE_ID = "jetson_orin_agx"
   ```

2. Run client:
   ```bash
   python src/jetson_logger.py
   ```

## Output Files

### Client Output: `logs/logs_*.csv`

Locally saved sensor readings with server-synchronized timestamps. Excel-compatible format with clearly labeled columns for plotting.

**IMX8 Client** (`logs/logs_YYYY-MM-DD_HH-MM-SS.csv`):
```
timestamp, obc_voltage_V, obc_current_mA, obc_power_mW, perif_voltage_V, perif_current_mA, perif_power_mW, jetson_voltage_V, jetson_current_mA, jetson_power_mW, obc_temp_C, perif_temp_C, jetson_temp_C, imx8_cpu_temp_C, jetson_thermal_zone0_C, ...
2026-04-13 14:30:45.123456, 5.0, 250.5, 1250.0, 12.0, 50.1, 601.2, 3.3, 150.2, 495.7, 35.25, 42.50, 38.75
2026-04-13 14:30:45.223456, 5.01, 251.2, 1255.6, 12.01, 50.3, 603.6, 3.31, 151.0, 499.6, 35.31, 42.56, 38.81
2026-04-13 14:30:45.323456, 4.99, 249.8, 1249.0, 11.99, 49.9, 599.8, 3.29, 149.4, 491.8, 35.19, 42.44, 38.69
```

**Jetson Client** (`logs/jetson_logs_YYYY-MM-DD_HH-MM-SS.csv`):
```
timestamp, device_id, [empty INA/MCP columns], imx8_cpu_temp_C, jetson_thermal_zone0_C, jetson_thermal_zone1_C, ..., client_time
```

### Server Output: `received_data.csv` (Multi-Device Archive)

Unified archive with data from all connected clients (IMX8, Jetson, etc.). Server's authoritative timestamp and client device identification:

```
server_timestamp, device_id, obc_voltage_V, obc_current_mA, obc_power_mW, ..., imx8_cpu_temp_C, jetson_thermal_zone0_C, ..., jetson_thermal_zone9_C, client_time
2026-04-13 14:30:45.123456, 5.0, 250.5, 1250.0, 12.0, 50.1, 601.2, 3.3, 150.2, 495.7, 35.25, 42.50, 38.75, 2026-04-13 14:30:45.087654
2026-04-13 14:30:45.223456, 5.01, 251.2, 1255.6, 12.01, 50.3, 603.6, 3.31, 151.0, 499.6, 35.31, 42.56, 38.81, 2026-04-13 14:30:45.187654
2026-04-13 14:30:45.323456, 4.99, 249.8, 1249.0, 11.99, 49.9, 599.8, 3.29, 149.4, 491.8, 35.19, 42.44, 38.69, 2026-04-13 14:30:45.287654
```

**CSV Column Descriptions:**

- `server_timestamp`: Server's authoritative time (Excel recognizes as datetime)
- `device_id`: Source device identifier (`imx8`, `jetson_orin_agx`, etc.)
- `obc_voltage_V`, `perif_voltage_V`, `jetson_voltage_V`: Voltage in volts (INA260) - IMX8 only
- `obc_current_mA`, `perif_current_mA`, `jetson_current_mA`: Current in milliamps (INA260) - IMX8 only
- `obc_power_mW`, `perif_power_mW`, `jetson_power_mW`: Power in milliwatts (INA260) - IMX8 only
- `obc_temp_C`, `perif_temp_C`, `jetson_temp_C`: Temperature in Celsius (MCP9808) - IMX8 only
- `imx8_cpu_temp_C`: IMX8 SoC CPU temperature (Linux thermal zone) - IMX8 only
- `jetson_thermal_zone0_C` through `jetson_thermal_zone9_C`: Jetson thermal zones - Jetson only
- `client_time`: Client's local time when data was read (for diagnosing clock issues)

**Note:** If client and server timestamps differ significantly (see `client_time` vs `server_timestamp`), it indicates clock synchronization issues between devices.

## Troubleshooting

### Simulation Mode

To test without physical hardware:

```python
# config.py
SIMULATE_SENSOR = True  # Enable simulation mode
```

Generates realistic synthetic data:
- **INA260 simulated data**: Voltage (4.8-5.2V), Current (200-400mA), Power (1000-2000mW)
- **MCP9808 simulated data**: Temperature (20-60°C)

Perfect for testing the network, CSV output, and Excel plotting without hardware!

### "Connection refused" Error

**Problem:** Client can't connect to server.

**Solutions:**
- Ensure `receiver.py` is running on the server
- Check `SERVER_IP` in `config.py` is correct
- Verify server is on the same network (if testing on different machines)
- Check firewall isn't blocking port 8000

### "Warning: Could not connect to server" (Client continues)

**Problem:** Network unavailable but client still running.

**Solution:**
- This is normal! Client falls back to local time and continues recording
- Check server logs to see if data was received

### "ModuleNotFoundError: No module named 'smbus2'"

**Problem:** Library not installed.

**Solution:**
```bash
pip install smbus2
```

### Hardware Not Found / I2C Errors

**Problem:** "Error reading INA260" or "Error reading MCP9808" on client.

**Solutions:**
- Verify I2C devices are connected to correct pins
- Check I2C addresses:
  ```bash
  i2cdetect -y 1  # Linux/Raspberry Pi to see all devices
  ```
  You should see:
  - 0x19, 0x1A, 0x1B (MCP9808 temperature sensors)
  - 0x40, 0x41, 0x45 (INA260 power sensors)
- Verify `I2C_BUS` in `config.py` matches your system (usually 1 for Raspberry Pi)
- Set `SIMULATE_SENSOR = True` in `config.py` to test without hardware

### Timestamp Mismatch Between Machines

**Problem:** Client and server timestamps don't match (large differences).

**Solution:**
- Set server's clock to correct time (this is the authoritative source)
- All clients will sync to server's time
- Use NTP or manual time sync:
  ```bash
  # Linux/Raspberry Pi
  sudo ntpdate -s time.nist.gov
  
  # macOS
  sudo sntp -sS time.apple.com
  ```

### Excel Cannot Parse Timestamps

**Problem:** Excel doesn't recognize timestamps as datetime values.

**Solution:**
- Verify `TIMESTAMP_FORMAT` in `config.py` is: `"%Y-%m-%d %H:%M:%S.%f"`
- This format uses space (not T) between date and time, which Excel recognizes
- If timestamps still show as text in Excel, select the column and use Data → Text to Columns

## Advanced Usage

### Multiple Simultaneous Clients

The receiver uses **multi-threading** to handle multiple concurrent client connections. Devices can send data simultaneously without performance degradation.

**Example with IMX8 and Jetson clients:**

If both send at the same time:
```
server_timestamp, device_id, obc_voltage_V, ..., imx8_cpu_temp_C, jetson_thermal_zone0_C, ..., client_time
2026-04-13 14:30:45.123456, imx8, 5.0, ..., 45.2, , , 2026-04-13 14:30:45.087654
2026-04-13 14:30:45.124567, jetson_orin_agx, , , , 72.1, 65.3, 2026-04-13 14:30:45.088765
```

All devices use the same server as their time authority, ensuring synchronized timestamps across all machines.

> **See [MULTI_CLIENT_README.md](MULTI_CLIENT_README.md)** for detailed multi-device setup, network configuration, and plotting examples.

### Excel Plotting

After data collection, import CSV into Excel:

1. **Open Excel** → **File** → **Open** → Select `logs/logs.csv` or `received_data.csv`
2. **Data** → **Charts** to create plots:
   - Plot `obc_temp_C` vs `timestamp` to see temperature over time
   - Plot `obc_voltage_V` vs `obc_current_mA` to see power curve
   - Plot `jetson_power_mW` vs `timestamp` for power draw trending
3. **Column headers** are automatically recognized as chart labels

### Monitoring Real-Time

While programs are running, view live data:

```bash
# Watch client logs
tail -f logs/logs.csv

# Watch server archive (in another terminal)
tail -f received_data.csv
```

## Testing

### Running Unit Tests

Comprehensive tests are available to verify CSV generation, timestamp synchronization, and data aggregation:

```bash
# Run all tests
cd tests/
python test_unified_csv.py

# Or from the thermal_logger root:
python -m pytest tests/
```

**Tests validate:**
- CSV header generation from multiple client types
- Timestamp synchronization across devices
- Multi-client data row generation
- Server aggregation logic
- Data column ordering and structure

### Manual Testing

1. **Simulation Mode** - Test without hardware:
   ```python
   # config/config_imx8.py
   SIMULATE_SENSOR = True  # Enables synthetic sensor data
   ```

2. **Local Network Test** - All on same machine:
   ```bash
   # Terminal 1: Server
   python src/receiver.py
   
   # Terminal 2: IMX8 Client
   python src/imx8x_logger.py
   
   # Terminal 3: Jetson Client (optional)
   python src/jetson_logger.py
   ```

3. **Remote Network Test** - Edit configs and deploy to actual devices

## Data Sampling / Decimation

Control how often data is saved to reduce file size while maintaining high read frequency:

```python
# config.py
SAVE_EVERY = 1    # Save all readings (no decimation) - default
SAVE_EVERY = 5    # Save every 5th reading (80% reduction)
SAVE_EVERY = 10   # Save every 10th reading (90% reduction)
```

**Example with SAVE_EVERY = 10:**
- Sensors read every 0.1 seconds (READ_INTERVAL)
- Data saved every 1 second (READ_INTERVAL × SAVE_EVERY)
- Console shows `[SKIPPED]` for readings not saved to file
- Only saved readings are sent over network to server

This allows high-frequency monitoring while keeping storage and bandwidth requirements low.

## Performance Notes

- Network latency: Typically <10ms over local network
- Each reading cycle: ~100ms (configurable via `READ_INTERVAL`)
- File I/O: Non-blocking, won't affect sensor readings
- Multi-threading server: Handles multiple concurrent connections without performance degradation

## Server Configuration

**`config/config_server.py`** settings:

```python
SERVER_LISTEN_IP = "0.0.0.0"      # Listen on all interfaces
SERVER_PORT = 8000                 # Port for client connections
SERVER_OUTPUT_FILE = "received_data.csv"  # Server-side archive
DEBUG = False                      # Enable verbose logging
SOCKET_TIMEOUT = 5.0               # Client connection timeout
SOCKET_BUFFER_SIZE = 4096          # Network buffer size
```

## Future Enhancements

Possible improvements:
- Database backend instead of CSV
- Real-time visualization dashboard
- Multi-client aggregation (already implemented!)
- Data compression for long-term storage
- SSL/TLS encryption for network transmission

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review terminal output for error messages
3. Verify config files in `config/` directory match your hardware setup
4. Enable `DEBUG = True` in config files for verbose output
5. Consult [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for detailed configuration help
6. See [MULTI_CLIENT_README.md](MULTI_CLIENT_README.md) for multi-device setup
7. Run tests with `python tests/test_unified_csv.py` to verify installation
