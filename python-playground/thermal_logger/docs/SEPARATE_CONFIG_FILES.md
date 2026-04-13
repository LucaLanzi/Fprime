# Separate Configuration Files - Summary

## What Changed

The system has been reorganized from a **single shared config** to **separate configuration files** for each component. This allows independent customization of network settings, sampling rates, and hardware configuration.

## New File Structure

```
python-playground/
├── config_server.py          ← Server configuration (receiver.py)
├── config_imx8.py            ← IMX8 client configuration (imx8x_logger.py)
├── config_jetson.py          ← Jetson client configuration (jetson_logger.py)
│
├── receiver.py               ← Uses config_server.py
├── imx8x_logger.py           ← Uses config_imx8.py
├── jetson_logger.py          ← Uses config_jetson.py
│
├── config.py                 ← (Legacy - kept for reference, no longer used)
├── README.md                 ← Project overview
├── MULTI_CLIENT_README.md    ← Multi-device setup guide
├── CONFIG_GUIDE.md           ← Detailed configuration reference (NEW)
└── logs/                     ← Output directory
    └── *.csv                 ← Generated logs
```

## Benefits

✅ **Independent Configuration** - Each component has its own settings file  
✅ **Clear Separation** - No confusion about which config is used where  
✅ **Network Flexibility** - Set different SERVER_IP for each client  
✅ **Sampling Control** - Each client can have different SAVE_EVERY rates  
✅ **Deployment Easy** - Copy just needed configs to each machine  
✅ **Multi-Rate Operation** - IMX8 at 10Hz, Jetson at 5Hz, both to same server

## Quick Start

### Development (Local Testing)

```bash
# All on one machine with simulated data
# (No changes needed - defaults are localhost + simulation)

# Terminal 1:
python3 receiver.py

# Terminal 2:
python3 imx8x_logger.py

# Terminal 3:
python3 jetson_logger.py
```

### Production (Network Deployment)

**Server Machine:**
```python
# config_server.py (no changes needed - defaults are good)
SERVER_LISTEN_IP = "0.0.0.0"
SERVER_PORT = 8000
```

**IMX8 Machine:**
```python
# config_imx8.py
SERVER_IP = "192.168.1.100"           # ← Change to server's IP
SIMULATE_SENSOR = False                # ← For real I2C sensors

# Settings
NUM_READINGS = 3600
SAVE_EVERY = 10
```

**Jetson Machine:**
```python
# config_jetson.py
JETSON_SERVER_IP = "192.168.1.100"    # ← Change to server's IP
SIMULATE_SENSOR = False                # ← For real thermal zones

# Settings
JETSON_NUM_READINGS = 3600
JETSON_SAVE_EVERY = 10
```

## Key Configuration Settings by Component

### Server (`config_server.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `SERVER_LISTEN_IP` | `"0.0.0.0"` | Listen on all interfaces |
| `SERVER_PORT` | `8000` | Client connection port |
| `DEBUG` | `True` | Verbose output |
| `SOCKET_TIMEOUT` | `5` | Client timeout (seconds) |

### IMX8 Client (`config_imx8.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `SERVER_IP` | `"127.0.0.1"` | Server to connect to |
| `CLIENT_DEVICE_ID` | `"imx8"` | Device name in CSV |
| `NUM_READINGS` | `20` | Samples to collect |
| `READ_INTERVAL` | `0.1` | Seconds between reads |
| `SAVE_EVERY` | `1` | Save every Nth reading |
| `SIMULATE_SENSOR` | `True` | Synthetic data |
| `I2C_BUS` | `1` | I2C bus number |

### Jetson Client (`config_jetson.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `JETSON_SERVER_IP` | `"127.0.0.1"` | Server to connect to |
| `JETSON_CLIENT_DEVICE_ID` | `"jetson_orin_agx"` | Device name in CSV |
| `JETSON_NUM_READINGS` | `20` | Samples to collect |
| `JETSON_READ_INTERVAL` | `0.1` | Seconds between reads |
| `JETSON_SAVE_EVERY` | `1` | Save every Nth reading |
| `SIMULATE_SENSOR` | `True` | Synthetic data |
| `MAX_THERMAL_ZONES` | `10` | Number of zones (0-9) |

## Configuration Patterns

### Scenario 1: Development Testing
All machines simulated, local network only.

```
# config_*.py files - use all defaults
No changes needed!
```

### Scenario 2: Single Device, Network Server
IMX8 on one machine sending to centralized server.

```python
# config_imx8.py changes:
SERVER_IP = "192.168.1.10"
SIMULATE_SENSOR = False

# config_server.py - no changes
```

### Scenario 3: Multiple Devices, Different Rates
IMX8 at high frequency, Jetson at low frequency.

```python
# config_imx8.py
SAVE_EVERY = 1        # Save all samples (10 Hz)

# config_jetson.py
JETSON_SAVE_EVERY = 10  # Save every 10th (1 Hz)

# Both send to same server, same CSV file
```

### Scenario 4: Bandwidth Optimization
Limited network, save only essential data.

```python
# config_imx8.py
NUM_READINGS = 3600       # 1 hour
READ_INTERVAL = 1         # Read every second
SAVE_EVERY = 60           # Save every minute (only 60 rows/hour)

# config_jetson.py
JETSON_NUM_READINGS = 3600
JETSON_READ_INTERVAL = 1
JETSON_SAVE_EVERY = 60

# Result: ~2 KB/hour per client
```

## Migration from Old Config

If you have an old single `config.py`:

1. **config_server.py** contains server-specific settings  
2. **config_imx8.py** contains IMX8-specific settings  
3. **config_jetson.py** contains Jetson-specific settings

Each new config file has detailed comments explaining each setting.

**Old config.py is kept as reference** (`config.py` - legacy, not used).

## Configuration Validation

Before running in production:

```bash
# Check all syntax
python3 -m py_compile config_server.py config_imx8.py config_jetson.py

# Test with simulation
SIMULATE_SENSOR=True
python3 receiver.py &
python3 imx8x_logger.py
python3 jetson_logger.py

# Verify CSV output
cat received_data.csv
```

## Deployment Checklist

- [ ] Identify server machine IP address
- [ ] Update `config_imx8.py`: Set `SERVER_IP` to server machine IP
- [ ] Update `config_jetson.py`: Set `JETSON_SERVER_IP` to server machine IP
- [ ] Set `SIMULATE_SENSOR = False` in both client configs
- [ ] Test connectivity: `ping server_ip`
- [ ] Start server: `python3 receiver.py`
- [ ] Start IMX8 client: `python3 imx8x_logger.py`
- [ ] Start Jetson client: `python3 jetson_logger.py` (optional)
- [ ] Verify data in `received_data.csv`

## Documentation

- **README.md** - Project overview and architecture
- **MULTI_CLIENT_README.md** - Multi-device network setup
- **CONFIG_GUIDE.md** - Detailed configuration reference with examples

## Questions?

See CONFIG_GUIDE.md for:
- Detailed setting explanations
- Common configuration patterns
- Troubleshooting configuration issues
- Bandwidth and sampling calculations
