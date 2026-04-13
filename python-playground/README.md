# Power and Temperature Sensor Data Collection System

A networked sensor data collection system that reads power monitoring data from INA260 sensors and temperature data from MCP9808 sensors, synchronizing timestamps across multiple machines.

## Overview

This system consists of two components:

- **Client** (`file_appender.py`): Reads INA260 (power) and MCP9808 (temperature) sensor data and sends it to the server
- **Server** (`receiver.py`): Receives data, acts as time authority, and archives to file

Both programs save timestamped data locally. The server's clock is the authoritative time source, ensuring synchronized timestamps even if individual devices have incorrect clocks.

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

```
┌─────────────────────────┐          TCP/IP          ┌──────────────────────┐
│  SENSOR DEVICE          │         (Port 8000)       │  SERVER/ARCHIVE      │
│  (file_appender.py)     │────────────────────────→  │  (receiver.py)       │
│                         │                           │                      │
│  3x INA260 Sensors      │←────────────────────────  │  Time Authority      │
│  3x MCP9808 Sensors     │   Timestamp Response      │  └─ received_data.csv│
│  └─ logs/logs.csv       │                           │                      │
└─────────────────────────┘                           └──────────────────────┘
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

## Configuration

Edit `config.py` to set your environment:

```python
# For local testing (both programs on same machine)
SERVER_IP = "127.0.0.1"

# For network testing (programs on different machines)
SERVER_IP = "192.168.1.100"  # Use server machine's actual IP
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

**INA260 Sensors** (Power Monitoring):
```python
SENSORS_INA260 = {
    'obc': {'address': 0x41, 'description': 'Onboard Computer Switching Regulator'},
    'perif': {'address': 0x45, 'description': 'Peripheral System Switching Regulator'},
    'jetson': {'address': 0x40, 'description': 'Jetson Switching Regulator'}
}
```

**MCP9808 Sensors** (Temperature):
```python
SENSORS_MCP9808 = {
    'obc': {'address': 0x19, 'description': 'Onboard Computer Temperature'},
    'perif': {'address': 0x1A, 'description': 'Peripheral System Temperature'},
    'jetson': {'address': 0x1B, 'description': 'Jetson Temperature'}
}
```

## Usage

### Local Testing (Same Machine)

**Terminal 1 - Start the server:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground
python receiver.py
```

**Terminal 2 - Run the client:**
```bash
cd /Users/luquito/Documents/GitHub/Fprime/python-playground
python file_appender.py
```

Expected output:

**Server Terminal:**
```
[SERVER] Configuration loaded from config.py
TIME AUTHORITY SERVER listening on 0.0.0.0:8000
[SERVER] Output file: received_data.csv
[SERVER] Note: Server saves all received data (sampling controlled by client)
Waiting for data from client...

Connection from ('127.0.0.1', 54321)
[SERVER TIME] 2026-04-13 14:30:45.123456 | obc:V5.0V,I250.5mA,P1250.0mW | perif:V12.0V,I50.1mA,P601.2mW | jetson:V3.3V,I150.2mA,P495.7mW | obc:T35.25C | perif:T42.50C | jetson:T38.75C
```

**Client Terminal:**
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
[SKIPPED] obc:V5.0V,I250.5mA jetson:V3.3V,I150.2mA perif:V12.0V,I50.1mA obc:T35.25C jetson:T38.75C perif:T42.50C (buffered, not sent)
time at 2
[SYNCED] [SAVED 1] obc:V5.01V,I251.2mA jetson:V3.31V,I151.0mA perif:V12.01V,I50.3mA obc:T35.31C jetson:T38.81C perif:T42.56C
```

### Network Testing (Different Machines)

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

**On Client/Sensor Machine:**

1. Edit `config.py`:
   ```python
   SERVER_IP = "192.168.1.100"  # Use your server's actual IP
   ```

2. Run client:
   ```bash
   python file_appender.py
   ```

## Output Files

### Client Output: `logs/logs.csv`

Locally saved sensor readings with server-synchronized timestamps. Excel-compatible format with clearly labeled columns for plotting:

```
timestamp, obc_voltage_V, obc_current_mA, obc_power_mW, perif_voltage_V, perif_current_mA, perif_power_mW, jetson_voltage_V, jetson_current_mA, jetson_power_mW, obc_temp_C, perif_temp_C, jetson_temp_C
2026-04-13 14:30:45.123456, 5.0, 250.5, 1250.0, 12.0, 50.1, 601.2, 3.3, 150.2, 495.7, 35.25, 42.50, 38.75
2026-04-13 14:30:45.223456, 5.01, 251.2, 1255.6, 12.01, 50.3, 603.6, 3.31, 151.0, 499.6, 35.31, 42.56, 38.81
2026-04-13 14:30:45.323456, 4.99, 249.8, 1249.0, 11.99, 49.9, 599.8, 3.29, 149.4, 491.8, 35.19, 42.44, 38.69
```

### Server Output: `received_data.csv`

Archived readings with server's authoritative timestamp and client's local time (for debugging clock synchronization):

```
server_timestamp, obc_voltage_V, obc_current_mA, obc_power_mW, perif_voltage_V, perif_current_mA, perif_power_mW, jetson_voltage_V, jetson_current_mA, jetson_power_mW, obc_temp_C, perif_temp_C, jetson_temp_C, client_time
2026-04-13 14:30:45.123456, 5.0, 250.5, 1250.0, 12.0, 50.1, 601.2, 3.3, 150.2, 495.7, 35.25, 42.50, 38.75, 2026-04-13 14:30:45.087654
2026-04-13 14:30:45.223456, 5.01, 251.2, 1255.6, 12.01, 50.3, 603.6, 3.31, 151.0, 499.6, 35.31, 42.56, 38.81, 2026-04-13 14:30:45.187654
2026-04-13 14:30:45.323456, 4.99, 249.8, 1249.0, 11.99, 49.9, 599.8, 3.29, 149.4, 491.8, 35.19, 42.44, 38.69, 2026-04-13 14:30:45.287654
```

**CSV Column Descriptions:**

- `timestamp` / `server_timestamp`: Server's authoritative time (Excel recognizes as datetime)
- `obc_voltage_V`, `perif_voltage_V`, `jetson_voltage_V`: Voltage in volts (INA260)
- `obc_current_mA`, `perif_current_mA`, `jetson_current_mA`: Current in milliamps (INA260)
- `obc_power_mW`, `perif_power_mW`, `jetson_power_mW`: Power in milliwatts (INA260)
- `obc_temp_C`, `perif_temp_C`, `jetson_temp_C`: Temperature in Celsius (MCP9808)
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

### Multiple Clients

Each client device can run its own `file_appender.py` instance, all sending to the same server.

**Server** (`received_data.csv`) receives data from multiple clients:
```
server_timestamp, obc_voltage_V, ..., jetson_temp_C, client_time
2026-04-13 14:30:45.123456, 5.0, ..., 38.75, 2026-04-13 14:30:45.087654
2026-04-13 14:30:45.125123, 5.02, ..., 38.78, 2026-04-13 14:30:45.089111
```

All devices use the same server as their time authority, ensuring synchronized timestamps.

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

## Future Enhancements

Possible improvements:
- Database backend instead of CSV
- Real-time visualization dashboard
- Multi-client aggregation
- Data compression for long-term storage
- SSL/TLS encryption for network transmission

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review terminal output for error messages
3. Verify `config.py` settings match your hardware setup
4. Enable `DEBUG = True` in `config.py` for verbose output
