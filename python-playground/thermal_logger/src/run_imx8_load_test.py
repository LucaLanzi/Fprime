#!/usr/bin/env python3
import datetime
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


LOGGER_CMD = [sys.executable, "/mnt/data/imx8x_logger_print.py"]
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


def main() -> int:
    duration = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DURATION
    cpu_method = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CPU_METHOD

    outdir = Path(os.environ.get("OUTDIR", str(Path.cwd() / f"imx8_load_test_{timestamp()}")))
    outdir.mkdir(parents=True, exist_ok=True)

    logger_log = outdir / "imx8_logger.log"
    stress_log = outdir / "imx8_stress.log"
    summary_log = outdir / "imx8_summary.txt"

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

            log_summary()
            log_summary(f"End time: {iso_now()}")
            log_summary(f"Logger log: {logger_log}")
            log_summary(f"Stress log: {stress_log}")

            if return_code != 0:
                print(f"IMX8 load test ended with stress-ng exit code {return_code}.")
                return return_code

            print("IMX8 load test complete.")
            return 0
        finally:
            stop_process(logger_proc, "logger")
            logger_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
