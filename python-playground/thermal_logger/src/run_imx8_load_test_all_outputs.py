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

LOGGER_CMD = [sys.executable, "/mnt/data/imx8x_logger_print.py"]
DEFAULT_DURATION = "10m"
DEFAULT_CPU_METHOD = "matrixprod"
PRINTED_LINE_RE = re.compile(r"^\[PRINTED\] \[SAMPLE (?P<sample>\d+)\] \[READ (?P<read>\d+)\] \[(?P<timestamp>[^\]]+)\] (?P<body>.*)$")
POWER_RE = re.compile(r"^(?P<sensor>[^:]+):V(?P<voltage>-?\d+(?:\.\d+)?)V,I(?P<current>-?\d+(?:\.\d+)?)mA,P(?P<power>-?\d+(?:\.\d+)?)mW$")
TEMP_RE = re.compile(r"^(?P<sensor>[^:]+):T(?P<temp>-?\d+(?:\.\d+)?)C$")


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


def parse_imx8_logger_log(log_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
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
            }

            for token in match.group("body").split():
                power_match = POWER_RE.match(token)
                if power_match:
                    sensor = power_match.group("sensor")
                    voltage = float(power_match.group("voltage"))
                    current = float(power_match.group("current"))
                    power = float(power_match.group("power"))
                    wide_row[f"{sensor}_voltage_v"] = voltage
                    wide_row[f"{sensor}_current_ma"] = current
                    wide_row[f"{sensor}_power_mw"] = power
                    long_rows.extend([
                        {
                            "sample": wide_row["sample"],
                            "read": wide_row["read"],
                            "timestamp": wide_row["timestamp"],
                            "sensor": sensor,
                            "metric": "voltage_v",
                            "value": voltage,
                            "unit": "V",
                        },
                        {
                            "sample": wide_row["sample"],
                            "read": wide_row["read"],
                            "timestamp": wide_row["timestamp"],
                            "sensor": sensor,
                            "metric": "current_ma",
                            "value": current,
                            "unit": "mA",
                        },
                        {
                            "sample": wide_row["sample"],
                            "read": wide_row["read"],
                            "timestamp": wide_row["timestamp"],
                            "sensor": sensor,
                            "metric": "power_mw",
                            "value": power,
                            "unit": "mW",
                        },
                    ])
                    continue

                temp_match = TEMP_RE.match(token)
                if temp_match:
                    sensor = temp_match.group("sensor")
                    temp_c = float(temp_match.group("temp"))
                    key = f"{sensor.lower()}_temp_c" if sensor == "IMX8_CPU" else f"{sensor}_temp_c"
                    wide_row[key] = temp_c
                    long_rows.append(
                        {
                            "sample": wide_row["sample"],
                            "read": wide_row["read"],
                            "timestamp": wide_row["timestamp"],
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


def export_imx8_csv(logger_log: Path, wide_csv: Path, long_csv: Path) -> tuple[int, int]:
    wide_rows, long_rows = parse_imx8_logger_log(logger_log)

    wide_fieldnames = ["sample", "read", "timestamp"]
    extra_wide_fields = sorted({key for row in wide_rows for key in row.keys() if key not in wide_fieldnames})
    write_csv(wide_csv, wide_rows, wide_fieldnames + extra_wide_fields)

    long_fieldnames = ["sample", "read", "timestamp", "sensor", "metric", "value", "unit"]
    write_csv(long_csv, long_rows, long_fieldnames)

    return len(wide_rows), len(long_rows)


def main() -> int:
    duration = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DURATION
    cpu_method = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CPU_METHOD

    outdir = Path(os.environ.get("OUTDIR", str(Path.cwd() / f"imx8_load_test_{timestamp()}")))
    outdir.mkdir(parents=True, exist_ok=True)

    logger_log = outdir / "imx8_logger.log"
    stress_log = outdir / "imx8_stress.log"
    summary_log = outdir / "imx8_summary.txt"
    wide_csv = outdir / "imx8_logger_wide.csv"
    long_csv = outdir / "imx8_logger_long.csv"

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

        log_summary("=== IMX8 load test ===")
        log_summary(f"Start time: {iso_now()}")
        log_summary(f"Duration: {duration}")
        log_summary(f"CPU method: {cpu_method}")
        log_summary(f"Output directory: {outdir}")
        log_summary()

        print("Starting IMX8 logger...")
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

            wide_count, long_count = export_imx8_csv(logger_log, wide_csv, long_csv)
            log_summary(f"Wide CSV: {wide_csv}")
            log_summary(f"Long CSV: {long_csv}")
            log_summary(f"Printed samples exported to wide CSV: {wide_count}")
            log_summary(f"Metric rows exported to long CSV: {long_count}")

            if return_code != 0:
                print(f"IMX8 load test ended with stress-ng exit code {return_code}.")
                return return_code

            print("IMX8 load test complete.")
            return 0
        finally:
            stop_process(stress_proc, "stress-ng")
            stop_process(logger_proc, "logger")
            if not logger_fp.closed:
                logger_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
