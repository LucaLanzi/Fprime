# Project Structure

The python-playground project is now organized into logical folders for better maintainability:

## Directory Layout

```
python-playground/
├── config/                          # Configuration files
│   ├── config_server.py            # Server settings
│   ├── config_imx8.py              # IMX8 client settings
│   └── config_jetson.py            # Jetson client settings
│
├── src/                            # Source code (main programs)
│   ├── receiver.py                 # Central data collection server
│   ├── imx8x_logger.py             # IMX8 sensor client
│   └── jetson_logger.py            # Jetson thermal logger client
│
├── tests/                          # Unit tests
│   └── test_unified_csv.py         # Test for unified CSV output verification
│
├── docs/                           # Documentation
│   ├── README.md                   # Project overview and quick start
│   ├── CONFIG_GUIDE.md             # Detailed configuration reference
│   ├── MULTI_CLIENT_README.md      # Multi-device network setup guide
│   └── SEPARATE_CONFIG_FILES.md    # Configuration file structure guide
│
├── logs/                           # Output directory (auto-created)
│   ├── logs_*.csv                  # IMX8 client local logs
│   └── jetson_logs_*.csv           # Jetson client local logs
│
├── received_data.csv               # Server unified log (generated at runtime)
└── .gitignore                      # Git ignore file (recommended)
```

## Running Programs

### Using Absolute Paths (from python-playground root):
```bash
# Run server
python3 src/receiver.py

# Run IMX8 client
python3 src/imx8x_logger.py

# Run Jetson client
python3 src/jetson_logger.py

# Run tests
python3 tests/test_unified_csv.py
```

### From src/ directory:
```bash
cd src/
python3 receiver.py
python3 imx8x_logger.py
python3 jetson_logger.py
```

## Configuration

Edit the config files to customize behavior:

- **config/config_server.py** - Server networking and output settings
- **config/config_imx8.py** - IMX8 sensors, sampling rate, network address
- **config/config_jetson.py** - Jetson thermal zones, sampling rate

See `docs/CONFIG_GUIDE.md` for detailed configuration options.

## Documentation

- **README.md** - Project overview, architecture, installation
- **CONFIG_GUIDE.md** - Configuration reference with examples
- **MULTI_CLIENT_README.md** - Network setup for multiple devices
- **SEPARATE_CONFIG_FILES.md** - How separate configs work together

## Key Points

✅ Each component has independent configuration  
✅ Programs automatically find configs via sys.path manipulation  
✅ Organized folder structure for scalability  
✅ Unit tests (test_unified_csv.py) verify multi-device functionality  
✅ All files compile without errors  
✅ Backward compatible - same functionality, better organization
