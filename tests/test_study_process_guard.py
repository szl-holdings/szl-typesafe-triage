from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import study_process_guard as guard


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeProcess:
    def __init__(self, pid=4321):
        self.pid = pid
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("child", timeout)
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15


class FakeJob:
    def __init__(self):
        self.process = None
        self.active = 1
        self.resumed = False
        self.terminated = False
        self.closed = False

    def assign_and_resume(self, process):
        self.process = process
        self.resumed = True

    def active_processes(self):
        return self.active

    def terminate(self):
        self.terminated = True
        self.active = 0
        self.process.returncode = 99

    def close(self):
        self.closed = True


def result(stdout="70\n", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)


def test_telemetry_selects_exact_gpu_and_rejects_multiple_rows():
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return result("61\n")

    assert guard.read_gpu_temperature(2, run_command=runner) == 61
    assert "--id=2" in calls[0]
    with pytest.raises(guard.GuardFailure, match="exactly one"):
        guard.read_gpu_temperature(2, run_command=lambda *a, **k: result("61\n62\n"))


@pytest.mark.parametrize(
    "runner, message",
    [
        (lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("nvidia-smi", 5)),
         "failed or timed out"),
        (lambda *a, **k: result("not-a-temperature\n"), "not an integer"),
    ],
)
def test_telemetry_timeout_and_malformed_are_terminal(runner, message):
    with pytest.raises(guard.GuardFailure, match=message) as caught:
        guard.read_gpu_temperature(0, run_command=runner)
    assert caught.value.exit_code == guard.EXIT_TELEMETRY


def test_prelaunch_telemetry_failure_never_starts_child(tmp_path):
    launched = []
    with pytest.raises(guard.GuardFailure) as caught:
        guard.supervise(
            Path("python.exe"), ["work.py"], tmp_path / "run.log",
            max_seconds=10, thermal_celsius=78, gpu_index=3,
            run_command=lambda *a, **k: result("79\n"),
            popen_factory=lambda *a, **k: launched.append((a, k)),
        )
    assert caught.value.exit_code == guard.EXIT_THERMAL
    assert launched == []


def test_wallclock_trip_terminates_child_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    clock = FakeClock()
    process = FakeProcess()
    job = FakeJob()
    commands = []

    def runner(command, **kwargs):
        commands.append(command)
        if command[0] == "taskkill.exe":
            process.returncode = 1
            return result("")
        return result("50\n")

    with pytest.raises(guard.GuardFailure) as caught:
        guard.supervise(
            Path("python.exe"), ["work.py"], tmp_path / "run.log",
            max_seconds=2, thermal_celsius=78, gpu_index=0, skip_gpu=True,
            popen_factory=lambda *a, **k: process, run_command=runner,
            monotonic=clock.monotonic, sleep=clock.sleep,
            windows_job_factory=lambda: job,
        )
    assert caught.value.exit_code == guard.EXIT_WALLCLOCK
    assert job.resumed and job.terminated and job.closed


def test_thermal_trip_terminates_child_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    clock = FakeClock()
    process = FakeProcess()
    job = FakeJob()
    temperatures = iter((50, 80))

    def runner(command, **kwargs):
        if command[0] == "taskkill.exe":
            process.returncode = 1
            return result("")
        return result("{}\n".format(next(temperatures)))

    with pytest.raises(guard.GuardFailure) as caught:
        guard.supervise(
            Path("python.exe"), ["work.py"], tmp_path / "run.log",
            max_seconds=20, thermal_celsius=78, gpu_index=1,
            popen_factory=lambda *a, **k: process, run_command=runner,
            monotonic=clock.monotonic, sleep=clock.sleep,
            telemetry_seconds=1,
            windows_job_factory=lambda: job,
        )
    assert caught.value.exit_code == guard.EXIT_THERMAL
    assert job.terminated and job.closed


def test_descendants_remain_guarded_after_root_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    clock = FakeClock()
    process = FakeProcess()
    process.returncode = 0  # The root has exited; its descendant remains in the job.
    job = FakeJob()
    with pytest.raises(guard.GuardFailure) as caught:
        guard.supervise(
            Path("python.exe"), ["work.py"], tmp_path / "run.log",
            max_seconds=2, thermal_celsius=78, gpu_index=0, skip_gpu=True,
            popen_factory=lambda *a, **k: process,
            monotonic=clock.monotonic, sleep=clock.sleep,
            windows_job_factory=lambda: job,
        )
    assert caught.value.exit_code == guard.EXIT_WALLCLOCK
    assert job.terminated


def test_unverified_descendant_termination_is_terminal(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    clock = FakeClock()
    process = FakeProcess()
    job = FakeJob()

    def failed_termination():
        raise guard.JobError("descendant survived")

    job.terminate = failed_termination
    with pytest.raises(guard.GuardFailure, match="not verified") as caught:
        guard.supervise(
            Path("python.exe"), ["work.py"], tmp_path / "run.log",
            max_seconds=2, thermal_celsius=78, gpu_index=0, skip_gpu=True,
            popen_factory=lambda *a, **k: process,
            monotonic=clock.monotonic, sleep=clock.sleep,
            windows_job_factory=lambda: job,
        )
    assert caught.value.exit_code == guard.EXIT_TERMINATION
    assert job.closed


def test_failed_taskkill_is_terminal(monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    process = FakeProcess()
    with pytest.raises(guard.GuardFailure, match="returned a failure") as caught:
        guard.terminate_process_tree(
            process, run_command=lambda *a, **k: result("", returncode=1),
        )
    assert caught.value.exit_code == guard.EXIT_TERMINATION


def test_surviving_child_after_taskkill_is_terminal(monkeypatch):
    monkeypatch.setattr(guard.os, "name", "nt")
    process = FakeProcess()
    with pytest.raises(guard.GuardFailure, match="survived") as caught:
        guard.terminate_process_tree(
            process, run_command=lambda *a, **k: result("", returncode=0),
        )
    assert caught.value.exit_code == guard.EXIT_TERMINATION


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows Job Object integration")
def test_native_job_terminates_cpu_descendant_after_parent_exits(tmp_path):
    observed = {}

    class ObservedJob(guard.WindowsJob):
        def terminate(self, timeout_seconds=10.0):
            observed["active_before_termination"] = self.active_processes()
            super().terminate(timeout_seconds)
            observed["active_after_termination"] = self.active_processes()

    # The supervised parent exits immediately after spawning a CPU-only sleeper.
    # The descendant remains in the job and must keep the supervisor alive until
    # the wall-clock guard terminates and verifies the complete job.
    program = (
        "import subprocess, sys; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        "print('descendant', child.pid, flush=True)"
    )
    with pytest.raises(guard.GuardFailure) as caught:
        guard.supervise(
            Path(sys.executable), ["-c", program], tmp_path / "native-job.log",
            max_seconds=1.0, thermal_celsius=78, gpu_index=0, skip_gpu=True,
            windows_job_factory=ObservedJob,
        )
    assert caught.value.exit_code == guard.EXIT_WALLCLOCK
    assert observed["active_before_termination"] >= 1
    assert observed["active_after_termination"] == 0
