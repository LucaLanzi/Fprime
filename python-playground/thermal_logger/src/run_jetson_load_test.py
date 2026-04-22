#!/usr/bin/env python3
import datetime
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


LOGGER_CMD = [sys.executable, "/mnt/data/jetson_logger_print.py"]
DEFAULT_DURATION = "10m"
DEFAULT_CPU_METHOD = "matrixprod"


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


def main() -> int:
    duration = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DURATION
    cpu_method = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CPU_METHOD
    enable_max_perf = os.environ.get("ENABLE_MAX_PERF", "1") == "1"

    outdir = Path(os.environ.get("OUTDIR", str(Path.cwd() / f"jetson_load_test_{timestamp()}")))
    outdir.mkdir(parents=True, exist_ok=True)

    logger_log = outdir / "jetson_logger.log"
    stress_log = outdir / "jetson_stress.log"
    summary_log = outdir / "jetson_summary.txt"

    if shutil.which("stress-ng") is None:
        print("stress-ng is not installed. Install it with: sudo apt update && sudo apt install -y stress-ng")
        return 1

    logger_proc: subprocess.Popen | None = None

    def cleanup(*_: object) -> None:
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

            log_summary()
            log_summary(f"End time: {iso_now()}")
            log_summary(f"Logger log: {logger_log}")
            log_summary(f"Stress log: {stress_log}")

            if return_code != 0:
                print(f"Jetson load test ended with stress-ng exit code {return_code}.")
                return return_code

            print("Jetson load test complete.")
            return 0
        finally:
            stop_process(logger_proc, "logger")
            logger_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
