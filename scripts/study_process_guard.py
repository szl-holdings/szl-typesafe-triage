"""Run one study Python command under fail-closed host guards.

This module deliberately imports no ML package.  It probes exactly one selected
physical GPU before launch and while the child is alive, enforces a hard
wall-clock deadline, and verifies Windows descendant-tree termination after a
guard trip.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

from study_windows_job import JobError, WindowsJob


EXIT_TELEMETRY = 96
EXIT_WALLCLOCK = 97
EXIT_THERMAL = 98
EXIT_TERMINATION = 99


class GuardFailure(RuntimeError):
    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


def read_gpu_temperature(
    gpu_index: int,
    *,
    run_command: Callable = subprocess.run,
    timeout_seconds: float = 5.0,
) -> int:
    """Return one temperature for the selected GPU or fail closed."""
    if timeout_seconds <= 0:
        raise GuardFailure("no telemetry wall-clock budget remains", EXIT_WALLCLOCK)
    command = [
        "nvidia-smi.exe",
        "--id={}".format(gpu_index),
        "--query-gpu=temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = run_command(
            command, capture_output=True, text=True, timeout=timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GuardFailure("GPU telemetry command failed or timed out", EXIT_TELEMETRY) from exc
    if result.returncode != 0:
        raise GuardFailure("GPU telemetry command returned a failure", EXIT_TELEMETRY)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise GuardFailure("GPU telemetry did not return exactly one selected device", EXIT_TELEMETRY)
    try:
        value = int(lines[0])
    except ValueError as exc:
        raise GuardFailure("GPU telemetry was not an integer temperature", EXIT_TELEMETRY) from exc
    if not 0 <= value <= 150:
        raise GuardFailure("GPU telemetry temperature was outside the accepted range", EXIT_TELEMETRY)
    return value


def terminate_process_tree(
    process,
    *,
    run_command: Callable = subprocess.run,
    timeout_seconds: float = 10.0,
) -> None:
    """Terminate the child and descendants, then prove the root is gone."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            result = run_command(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GuardFailure("process-tree termination command failed or timed out",
                               EXIT_TERMINATION) from exc
        if result.returncode != 0:
            raise GuardFailure("process-tree termination command returned a failure",
                               EXIT_TERMINATION)
    else:  # Unit-test and developer fallback; the production runner is Windows-only.
        process.terminate()
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise GuardFailure("child survived process-tree termination", EXIT_TERMINATION) from exc
    if process.poll() is None:
        raise GuardFailure("child survived process-tree termination", EXIT_TERMINATION)


def supervise(
    python: Path,
    command: Sequence[str],
    log: Path,
    *,
    max_seconds: float,
    thermal_celsius: int,
    gpu_index: int,
    skip_gpu: bool = False,
    poll_seconds: float = 1.0,
    telemetry_seconds: float = 5.0,
    popen_factory: Callable = subprocess.Popen,
    run_command: Callable = subprocess.run,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    windows_job_factory: Callable = WindowsJob,
) -> int:
    """Supervise one child. Guard failures raise ``GuardFailure``."""
    if max_seconds <= 0:
        raise GuardFailure("no wall-clock budget remains", EXIT_WALLCLOCK)
    if not command:
        raise ValueError("a Python command is required")
    started = monotonic()
    if not skip_gpu:
        temperature = read_gpu_temperature(
            gpu_index, run_command=run_command,
            timeout_seconds=min(5.0, max_seconds - (monotonic() - started)),
        )
        if monotonic() - started >= max_seconds:
            raise GuardFailure("pre-launch wall-clock guard exceeded", EXIT_WALLCLOCK)
        if temperature >= thermal_celsius:
            raise GuardFailure(
                "pre-launch thermal guard reached {} C".format(temperature), EXIT_THERMAL,
            )

    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    job = None
    if os.name == "nt":
        try:
            job = windows_job_factory()
        except (OSError, JobError) as exc:
            raise GuardFailure("cannot establish child process job", EXIT_TERMINATION) from exc
        creationflags |= WindowsJob.CREATE_SUSPENDED

    def terminate_tree(process):
        if job is not None:
            try:
                job.terminate()
                process.wait(timeout=10.0)
                if job.active_processes() != 0:
                    raise JobError("a descendant survived process job termination")
            except (OSError, JobError, subprocess.TimeoutExpired) as exc:
                raise GuardFailure("process job termination was not verified",
                                   EXIT_TERMINATION) from exc
        else:
            terminate_process_tree(process, run_command=run_command)

    with log.open("w", encoding="utf-8", newline="\n") as handle:
        try:
            if monotonic() - started >= max_seconds:
                raise GuardFailure("pre-launch wall-clock guard exceeded", EXIT_WALLCLOCK)
            process = popen_factory(
                [str(python), *command],
                cwd=str(Path.cwd()),
                stdout=handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
            if job is not None:
                try:
                    job.assign_and_resume(process)
                except (OSError, JobError) as exc:
                    # A denied assignment leaves the child suspended. Terminate
                    # it directly as well as closing any partially assigned job.
                    terminate_process_tree(process, run_command=run_command)
                    raise GuardFailure("suspended child job assignment or resume failed",
                                       EXIT_TERMINATION) from exc
            last_telemetry = started
            while True:
                returncode = process.poll()
                if returncode is not None and (job is None or job.active_processes() == 0):
                    return int(returncode)
                current = monotonic()
                if current - started >= max_seconds:
                    terminate_tree(process)
                    raise GuardFailure("wall-clock guard exceeded", EXIT_WALLCLOCK)
                if not skip_gpu and current - last_telemetry >= telemetry_seconds:
                    try:
                        temperature = read_gpu_temperature(
                            gpu_index, run_command=run_command,
                            timeout_seconds=min(5.0, max_seconds - (monotonic() - started)),
                        )
                    except GuardFailure:
                        terminate_tree(process)
                        raise
                    if temperature >= thermal_celsius:
                        terminate_tree(process)
                        raise GuardFailure(
                            "thermal guard reached {} C".format(temperature), EXIT_THERMAL,
                        )
                    current = monotonic()
                    if current - started >= max_seconds:
                        terminate_tree(process)
                        raise GuardFailure("wall-clock guard exceeded", EXIT_WALLCLOCK)
                    last_telemetry = current
                sleep(min(poll_seconds, max_seconds - (current - started)))
        except JobError as exc:
            terminate_tree(process)
            raise GuardFailure("process job accounting failed", EXIT_TERMINATION) from exc
        finally:
            if job is not None:
                job.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--python", type=Path, required=True)
    result.add_argument("--log", type=Path, required=True)
    result.add_argument("--max-seconds", type=float, required=True)
    result.add_argument("--thermal-celsius", type=int, default=78)
    result.add_argument("--gpu-index", type=int, default=0)
    result.add_argument("--skip-gpu", action="store_true")
    result.add_argument("command", nargs=argparse.REMAINDER)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    try:
        return supervise(
            args.python,
            command,
            args.log,
            max_seconds=args.max_seconds,
            thermal_celsius=args.thermal_celsius,
            gpu_index=args.gpu_index,
            skip_gpu=args.skip_gpu,
        )
    except GuardFailure as exc:
        print("PROCESS_GUARD_REFUSE: {}".format(exc), file=sys.stderr, flush=True)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
