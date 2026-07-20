"""Tests del provisionamiento reproducible de Chromium para los gates E2E."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "playwright_runtime.py"


def _module():
    spec = importlib.util.spec_from_file_location("exportbot_playwright_runtime", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_ensure_chromium_installs_matching_browser_when_probe_fails(monkeypatch, tmp_path):
    runtime = _module()
    probes = iter([_result(1, stderr="browser missing"), _result(0, stdout="chromium= test")])
    commands: list[list[str]] = []

    monkeypatch.setattr(runtime, "_probe", lambda _env: next(probes))

    def fake_run(command, env, timeout=900):
        commands.append(command)
        assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
        return _result(0)

    monkeypatch.setattr(runtime, "_run", fake_run)
    env = runtime.ensure_chromium({"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)})

    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
    assert [runtime.sys.executable, "-m", "playwright", "install", "chromium"] in commands


def test_playwright_environment_preserves_explicit_shared_cache(tmp_path):
    runtime = _module()
    env = runtime.playwright_environment({"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)})
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
    assert tmp_path.is_dir()
