#!/usr/bin/env python3
"""
Unit test to verify receiver.py generates one unified CSV file
with data from multiple clients (IMX8 and Jetson).

This test runs all components locally with simulation enabled.
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
    Test that receiver.py generates one unified CSV file with:
    1. Data from IMX8 client (device_id='imx8')
    2. Data from Jetson client (device_id='jetson_orin_agx')
    3. Proper CSV structure with device_id column
    """
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Unit Test: Unified Receiver CSV Output{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    # Configuration
    OUTPUT_FILE = "received_data.csv"
    OUTPUT_PATH = OUTPUT_FILE  # In current directory (PROJECT_ROOT)
    NUM_READINGS = 5  # Quick test - 5 readings each
    
    # Clean up old output
    if os.path.exists(OUTPUT_PATH):
        os.remove(OUTPUT_PATH)
        print_status("INFO", f"Cleaned up old {OUTPUT_FILE}")
    
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
        
        imx8_stdout, imx8_stderr = imx8_proc.communicate(timeout=10)
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
        
        jetson_stdout, jetson_stderr = jetson_proc.communicate(timeout=10)
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
    
    # Verify output file exists
    print_status("INFO", "Verifying output CSV file...")
    
    if not os.path.exists(OUTPUT_PATH):
        print_status("FAIL", f"{OUTPUT_FILE} was not created at {OUTPUT_PATH}")
        return False
    
    print_status("PASS", f"{OUTPUT_FILE} exists at {OUTPUT_PATH}")
    
    # Read and analyze CSV
    print_status("INFO", "Analyzing CSV structure and content...")
    
    try:
        with open(OUTPUT_PATH, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            print_status("FAIL", "CSV file is empty")
            return False
        
        print_status("PASS", f"CSV has {len(rows)} rows of data")
        
        # Check for device_id column
        if 'device_id' not in rows[0]:
            print_status("FAIL", "CSV missing 'device_id' column")
            return False
        
        print_status("PASS", "CSV has 'device_id' column")
        
        # Extract device IDs
        device_ids = set()
        for row in rows:
            device_id = row.get('device_id', '')
            if device_id:
                device_ids.add(device_id)
        
        print_status("INFO", f"Found device_ids: {device_ids}")
        
        # Verify we have data from both clients
        imx8_rows = [r for r in rows if r.get('device_id') == 'imx8']
        jetson_rows = [r for r in rows if r.get('device_id') == 'jetson_orin_agx']
        
        print_status("INFO", f"IMX8 rows: {len(imx8_rows)}")
        print_status("INFO", f"Jetson rows: {len(jetson_rows)}")
        
        if len(imx8_rows) == 0:
            print_status("FAIL", "No IMX8 data in CSV (expected at least 1 row)")
            return False
        
        print_status("PASS", f"IMX8 client data present ({len(imx8_rows)} rows)")
        
        if len(jetson_rows) == 0:
            print_status("FAIL", "No Jetson data in CSV (expected at least 1 row)")
            return False
        
        print_status("PASS", f"Jetson client data present ({len(jetson_rows)} rows)")
        
        # Verify CSV has all expected columns
        expected_cols = [
            'server_timestamp', 'device_id', 
            'imx8_cpu_temp_C', 'jetson_thermal_zone0_C',
            'client_time'
        ]
        
        missing_cols = [c for c in expected_cols if c not in rows[0]]
        
        if missing_cols:
            print_status("WARN", f"Missing expected columns: {missing_cols}")
        else:
            print_status("PASS", "All expected columns present")
        
        # Verify IMX8 data structure
        print_status("INFO", "Checking IMX8 data structure...")
        imx8_sample = imx8_rows[0]
        
        if imx8_sample.get('imx8_cpu_temp_C') == '':
            print_status("FAIL", "IMX8 row: imx8_cpu_temp_C is empty")
            return False
        
        print_status("PASS", f"IMX8 row: imx8_cpu_temp_C = {imx8_sample.get('imx8_cpu_temp_C')}")
        
        # Verify Jetson rows have empty IMX8 columns
        jetson_sample = jetson_rows[0]
        if jetson_sample.get('imx8_cpu_temp_C') != '':
            print_status("WARN", f"Jetson row unexpectedly has imx8_cpu_temp_C = {jetson_sample.get('imx8_cpu_temp_C')}")
        else:
            print_status("PASS", "Jetson row correctly has empty imx8_cpu_temp_C")
        
        # Verify Jetson data structure
        print_status("INFO", "Checking Jetson data structure...")
        
        if jetson_sample.get('jetson_thermal_zone0_C') == '':
            print_status("FAIL", "Jetson row: jetson_thermal_zone0_C is empty")
            return False
        
        print_status("PASS", f"Jetson row: jetson_thermal_zone0_C = {jetson_sample.get('jetson_thermal_zone0_C')}")
        
        # Print sample rows
        print_status("INFO", "Sample CSV rows:")
        print("\n  IMX8 Sample:")
        for col in ['server_timestamp', 'device_id', 'imx8_cpu_temp_C', 'client_time']:
            if col in imx8_sample:
                print(f"    {col}: {imx8_sample[col]}")
        
        print("\n  Jetson Sample:")
        for col in ['server_timestamp', 'device_id', 'jetson_thermal_zone0_C', 'client_time']:
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
    print("RECEIVER UNIFIED CSV OUTPUT TEST")
    print("Testing that receiver.py generates one CSV with multiple devices")
    print("="*60)
    
    success = test_unified_csv_output()
    
    print(f"\n{'='*60}")
    if success:
        print(f"{Colors.GREEN}✓ TEST PASSED{Colors.END}")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print(f"{Colors.RED}✗ TEST FAILED{Colors.END}")
        print(f"{'='*60}\n")
        sys.exit(1)
