#!/usr/bin/env python3
"""
Unit test to verify receiver.py generates per-device CSV files
with data from multiple clients (IMX8 and Jetson).

This test runs all components locally with simulation enabled.
Expected files:
  - received_data_imx8.csv
  - received_data_jetson.csv
"""

import subprocess
import time
import os
import csv
import sys
import signal
from pathlib import Path

# Change to parent directory (python-playground) to match where receiver writes CSV
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)

# Color output for terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(status, message):
    """Print colored status message"""
    if status == "PASS":
        print(f"{Colors.GREEN}✓ PASS{Colors.END}: {message}")
    elif status == "FAIL":
        print(f"{Colors.RED}✗ FAIL{Colors.END}: {message}")
    elif status == "INFO":
        print(f"{Colors.BLUE}ℹ INFO{Colors.END}: {message}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠ WARN{Colors.END}: {message}")

def test_unified_csv_output():
    """
    Test that receiver.py generates per-device CSV files with:
    1. received_data_imx8.csv from IMX8 client
    2. received_data_jetson.csv from Jetson client
    3. Proper CSV structure without device_id column (implicit in filename)
    """
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Unit Test: Per-Device Receiver CSV Output{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    # Configuration
    OUTPUT_FILES = {
        'imx8': "received_data_imx8.csv",
        'jetson_orin_agx': "received_data_jetson_orin_agx.csv"
    }
    NUM_READINGS = 5  # Quick test - 5 readings each
    
    # Clean up old output
    for device_id, filename in OUTPUT_FILES.items():
        if os.path.exists(filename):
            os.remove(filename)
            print_status("INFO", f"Cleaned up old {filename}")
    
    print_status("INFO", "Starting receiver server...")
    
    # Start receiver in background
    receiver_proc = subprocess.Popen(
        ["python3", "src/receiver.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )
    
    # Give server time to start
    time.sleep(1)
    
    if receiver_proc.poll() is not None:
        print_status("FAIL", "Receiver failed to start")
        stdout, stderr = receiver_proc.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False
    
    print_status("PASS", "Receiver server started")
    
    try:
        # Run IMX8 client
        print_status("INFO", "Running IMX8 client...")
        imx8_proc = subprocess.Popen(
            ["python3", "src/imx8x_logger.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env={**os.environ, 'PYTHONPATH': str(Path(__file__).parent.parent / 'config')}
        )
        
        imx8_stdout, imx8_stderr = imx8_proc.communicate(timeout=30)
        print_status("PASS", "IMX8 client completed")
        
        # Wait a moment between clients
        time.sleep(0.5)
        
        # Run Jetson client
        print_status("INFO", "Running Jetson client...")
        jetson_proc = subprocess.Popen(
            ["python3", "src/jetson_logger.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env={**os.environ, 'PYTHONPATH': str(Path(__file__).parent.parent / 'config')}
        )
        
        jetson_stdout, jetson_stderr = jetson_proc.communicate(timeout=30)
        print_status("PASS", "Jetson client completed")
        
        # Give server time to write final data
        time.sleep(1)
        
    finally:
        # Stop receiver
        print_status("INFO", "Stopping receiver server...")
        receiver_proc.terminate()
        try:
            receiver_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            receiver_proc.kill()
            receiver_proc.wait()
        print_status("PASS", "Receiver stopped")
    
    # Verify output files exist
    print_status("INFO", "Verifying output CSV files...")
    
    files_exist = {}
    for device_id, filename in OUTPUT_FILES.items():
        if not os.path.exists(filename):
            print_status("FAIL", f"{filename} was not created")
            return False
        files_exist[device_id] = True
        print_status("PASS", f"{filename} exists")
    
    # Read and analyze both CSV files
    print_status("INFO", "Analyzing CSV structure and content...")
    
    try:
        # Read IMX8 CSV
        with open(OUTPUT_FILES['imx8'], 'r') as f:
            imx8_reader = csv.DictReader(f)
            imx8_rows = list(imx8_reader)
        
        if not imx8_rows:
            print_status("FAIL", "IMX8 CSV file is empty")
            return False
        
        print_status("PASS", f"IMX8 CSV has {len(imx8_rows)} rows of data")
        
        # Read Jetson CSV
        with open(OUTPUT_FILES['jetson_orin_agx'], 'r') as f:
            jetson_reader = csv.DictReader(f)
            jetson_rows = list(jetson_reader)
        
        if not jetson_rows:
            print_status("FAIL", "Jetson CSV file is empty")
            return False
        
        print_status("PASS", f"Jetson CSV has {len(jetson_rows)} rows of data")
        
        # Check that device_id column is NOT present (implicit in filename)
        if 'device_id' in imx8_rows[0]:
            print_status("FAIL", "IMX8 CSV should NOT have 'device_id' column (device is implicit in filename)")
            return False
        
        print_status("PASS", "IMX8 CSV correctly has no 'device_id' column")
        
        if 'device_id' in jetson_rows[0]:
            print_status("FAIL", "Jetson CSV should NOT have 'device_id' column (device is implicit in filename)")
            return False
        
        print_status("PASS", "Jetson CSV correctly has no 'device_id' column")
        
        # Verify CSV has all expected columns
        imx8_expected_cols = ['server_timestamp', 'jetson_voltage_V', 'jetson_current_mA', 'jetson_power_mW', 
                              'obc_voltage_V', 'obc_current_mA', 'obc_power_mW',
                              'perif_voltage_V', 'perif_current_mA', 'perif_power_mW',
                              'jetson_temp_C', 'obc_temp_C', 'perif_temp_C', 'imx8_cpu_temp_C', 'client_time']
        jetson_expected_cols = ['server_timestamp', 'jetson_thermal_zone0_C', 'jetson_thermal_zone9_C', 'client_time']
        
        imx8_missing_cols = [c for c in imx8_expected_cols if c not in imx8_rows[0]]
        jetson_missing_cols = [c for c in jetson_expected_cols if c not in jetson_rows[0]]
        
        if imx8_missing_cols:
            print_status("WARN", f"IMX8 CSV missing expected columns: {imx8_missing_cols}")
        else:
            print_status("PASS", "IMX8 CSV has all expected columns")
        
        if jetson_missing_cols:
            print_status("WARN", f"Jetson CSV missing expected columns: {jetson_missing_cols}")
        else:
            print_status("PASS", "Jetson CSV has all expected columns")
        
        # Verify IMX8 data structure
        print_status("INFO", "Checking IMX8 data structure...")
        imx8_sample = imx8_rows[0]
        
        if imx8_sample.get('imx8_cpu_temp_C') == '':
            print_status("FAIL", "IMX8 row: imx8_cpu_temp_C is empty")
            return False
        
        print_status("PASS", f"IMX8 row: imx8_cpu_temp_C = {imx8_sample.get('imx8_cpu_temp_C')}")
        
        # Verify Jetson data structure
        print_status("INFO", "Checking Jetson data structure...")
        jetson_sample = jetson_rows[0]
        
        if jetson_sample.get('jetson_thermal_zone0_C') == '':
            print_status("FAIL", "Jetson row: jetson_thermal_zone0_C is empty")
            return False
        
        print_status("PASS", f"Jetson row: jetson_thermal_zone0_C = {jetson_sample.get('jetson_thermal_zone0_C')}")
        
        # Print sample rows
        print_status("INFO", "Sample CSV rows:")
        print("\n  IMX8 Sample:")
        for col in ['server_timestamp', 'imx8_cpu_temp_C', 'client_time']:
            if col in imx8_sample:
                print(f"    {col}: {imx8_sample[col]}")
        
        print("\n  Jetson Sample:")
        for col in ['server_timestamp', 'jetson_thermal_zone0_C', 'client_time']:
            if col in jetson_sample:
                print(f"    {col}: {jetson_sample[col]}")
        
        print()
        print_status("PASS", "CSV validation complete - all checks passed!")
        return True
        
    except Exception as e:
        print_status("FAIL", f"Error reading CSV: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("RECEIVER PER-DEVICE CSV OUTPUT TEST")
    print("Testing that receiver.py generates separate CSVs per device")
    print("="*60)
    
    success = test_unified_csv_output()
    
    print(f"\n{'='*60}")
    if success:
        print(f"{Colors.GREEN}✓ TEST PASSED{Colors.END}")
        print(f"Per-device CSV files created successfully")
        print(f"  - received_data_imx8.csv")
        print(f"  - received_data_jetson_orin_agx.csv")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print(f"{Colors.RED}✗ TEST FAILED{Colors.END}")
        print(f"{'='*60}\n")
        sys.exit(1)
