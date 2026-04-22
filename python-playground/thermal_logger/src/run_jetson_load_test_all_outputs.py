#!/usr/bin/env python3
import csv
import datetime
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

LOGGER_CMD = [sys.executable, "/mnt/data/jetson_logger_print.py"]
DEFAULT_DURATION = "10m"
DEFAULT_CPU_METHOD = "matrixprod"
PRINTED_LINE_RE = re.compile(r"^\[PRINTED\] \[SAMPLE (?P<sample>\d+)\] \[READ (?P<read>\d+)\] \[(?P<timestamp>[^\]]+)\] device_id:(?P<device_id>\S+)(?P<body>.*)$")
ZONE_RE = re.compile(r"^Zone(?P<zone>\d+):(?P<temp>-?\d+(?:\.\d+)?)C$")


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def stop_process(proc: subprocess.Popen | None, name: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    print(f"Stopping {name} (PID {proc.pid})...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def run_optional_command(cmd: list[str], summary_fp, description: str) -> None:
    print(description)
    summary_fp.write(description + "\n")
    summary_fp.flush()
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        summary_fp.write(result.stdout)
    if result.stderr:
        summary_fp.write(result.stderr)
    summary_fp.flush()
    if result.returncode != 0:
        warning = f"Warning: command failed with exit code {result.returncode}: {' '.join(cmd)}"
        print(warning)
        summary_fp.write(warning + "\n")
        summary_fp.flush()


def parse_jetson_logger_log(log_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    wide_rows: list[dict[str, object]] = []
    long_rows: list[dict[str, object]] = []

    with log_path.open("r", encoding="utf-8") as fp:
        for raw_line in fp:
            line = raw_line.strip()
            match = PRINTED_LINE_RE.match(line)
            if not match:
                continue

            wide_row: dict[str, object] = {
                "sample": int(match.group("sample")),
                "read": int(match.group("read")),
                "timestamp": match.group("timestamp"),
                "device_id": match.group("device_id"),
            }

            for token in match.group("body").split():
                zone_match = ZONE_RE.match(token)
                if not zone_match:
                    continue
                zone_num = zone_match.group("zone")
                temp_c = float(zone_match.group("temp"))
                sensor = f"zone_{zone_num}"
                wide_row[f"{sensor}_temp_c"] = temp_c
                long_rows.append(
                    {
                        "sample": wide_row["sample"],
                        "read": wide_row["read"],
                        "timestamp": wide_row["timestamp"],
                        "device_id": wide_row["device_id"],
                        "sensor": sensor,
                        "metric": "temp_c",
                        "value": temp_c,
                        "unit": "C",
                    }
                )

            wide_rows.append(wide_row)

    return wide_rows, long_rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_jetson_csv(logger_log: Path, wide_csv: Path, long_csv: Path) -> tuple[int, int]:
    wide_rows, long_rows = parse_jetson_logger_log(logger_log)

    wide_fieldnames = ["sample", "read", "timestamp", "device_id"]
    extra_wide_fields = sorted({key for row in wide_rows for key in row.keys() if key not in wide_fieldnames})
    write_csv(wide_csv, wide_rows, wide_fieldnames + extra_wide_fields)

    long_fieldnames = ["sample", "read", "timestamp", "device_id", "sensor", "metric", "value", "unit"]
    write_csv(long_csv, long_rows, long_fieldnames)

    return len(wide_rows), len(long_rows)


def main() -> int:
    duration = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DURATION
    cpu_method = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CPU_METHOD
    enable_max_perf = os.environ.get("ENABLE_MAX_PERF", "1") == "1"

    outdir = Path(os.environ.get("OUTDIR", str(Path.cwd() / f"jetson_load_test_{timestamp()}")))
    outdir.mkdir(parents=True, exist_ok=True)

    logger_log = outdir / "jetson_logger.log"
    stress_log = outdir / "jetson_stress.log"
    summary_log = outdir / "jetson_summary.txt"
    wide_csv = outdir / "jetson_logger_wide.csv"
    long_csv = outdir / "jetson_logger_long.csv"

    if shutil.which("stress-ng") is None:
        print("stress-ng is not installed. Install it with: sudo apt update && sudo apt install -y stress-ng")
        return 1

    logger_proc: subprocess.Popen | None = None
    stress_proc: subprocess.Popen | None = None

    def cleanup(*_: object) -> None:
        stop_process(stress_proc, "stress-ng")
        stop_process(logger_proc, "logger")

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, cleanup)

    with summary_log.open("w", encoding="utf-8") as summary_fp:
        def log_summary(line: str = "") -> None:
            print(line)
            summary_fp.write(line + "\n")
            summary_fp.flush()

        log_summary("=== Jetson load test ===")
        log_summary(f"Start time: {iso_now()}")
        log_summary(f"Duration: {duration}")
        log_summary(f"CPU method: {cpu_method}")
        log_summary(f"Output directory: {outdir}")
        log_summary()

        if enable_max_perf:
            if shutil.which("nvpmodel") is not None:
                run_optional_command(["sudo", "nvpmodel", "-m", "0"], summary_fp, "Setting max Jetson power mode with nvpmodel -m 0")
                run_optional_command(["sudo", "nvpmodel", "-q"], summary_fp, "Current nvpmodel:")
            else:
                log_summary("nvpmodel not found; skipping power mode configuration")

            if shutil.which("jetson_clocks") is not None:
                run_optional_command(["sudo", "jetson_clocks"], summary_fp, "Applying jetson_clocks")
            else:
                log_summary("jetson_clocks not found; skipping max clocks")

        print("Starting Jetson logger...")
        logger_fp = logger_log.open("w", encoding="utf-8")
        try:
            logger_proc = subprocess.Popen(
                LOGGER_CMD,
                stdout=logger_fp,
                stderr=subprocess.STDOUT,
                text=True,
            )
            log_summary(f"Logger PID: {logger_proc.pid}")

            time.sleep(2)

            print("Running stress-ng...")
            with stress_log.open("w", encoding="utf-8") as stress_fp:
                stress_cmd = [
                    "stress-ng",
                    "--cpu",
                    "0",
                    "--cpu-method",
                    cpu_method,
                    "--metrics-brief",
                    "--timeout",
                    duration,
                ]
                stress_proc = subprocess.Popen(
                    stress_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                assert stress_proc.stdout is not None
                for line in stress_proc.stdout:
                    print(line, end="")
                    stress_fp.write(line)
                return_code = stress_proc.wait()
                stress_proc = None

            log_summary()
            log_summary(f"End time: {iso_now()}")
            log_summary(f"Logger log: {logger_log}")
            log_summary(f"Stress log: {stress_log}")

            logger_fp.flush()
            stop_process(logger_proc, "logger")
            logger_proc = None
            logger_fp.close()

            wide_count, long_count = export_jetson_csv(logger_log, wide_csv, long_csv)
            log_summary(f"Wide CSV: {wide_csv}")
            log_summary(f"Long CSV: {long_csv}")
            log_summary(f"Printed samples exported to wide CSV: {wide_count}")
            log_summary(f"Metric rows exported to long CSV: {long_count}")

            if return_code != 0:
                print(f"Jetson load test ended with stress-ng exit code {return_code}.")
                return return_code

            print("Jetson load test complete.")
            return 0
        finally:
            stop_process(stress_proc, "stress-ng")
            stop_process(logger_proc, "logger")
            if not logger_fp.closed:
                logger_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
