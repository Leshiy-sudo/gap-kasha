import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from autotest_admin import (  # noqa: E402
    UI_TEST_CLASSES,
    find_adb,
    mark_run_finished,
    mark_run_started,
    mark_suite_finished,
    mark_suite_started,
    normalize_requested_suites,
    resolve_android_serial,
    tail_output,
)

APP_PACKAGE = "com.gapkassa"
ANDROID_TEST_RESULTS_DIR = REPO_ROOT / "app" / "build" / "outputs" / "androidTest-results" / "connected" / "debug"


def run_command(command: List[str], *, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    started_at = time.monotonic()
    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_sec = time.monotonic() - started_at
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return {
        "exit_code": result.returncode,
        "duration_sec": duration_sec,
        "output": output,
    }


def run_adb(serial: str, args: List[str], *, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    adb_path = (env or {}).get("ADB_PATH") or find_adb() or "adb"
    return run_command([adb_path, "-s", serial, *args], env=env)


def find_latest_android_artifact(*parts: str) -> Optional[Path]:
    if not ANDROID_TEST_RESULTS_DIR.exists():
        return None
    matches = list(ANDROID_TEST_RESULTS_DIR.glob(str(Path("*", *parts))))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def collect_android_failure_diagnostics(test_class: str) -> str:
    class_name, _, method_name = test_class.partition("#")
    snippets: List[str] = []

    logcat_path = find_latest_android_artifact(f"logcat-{class_name}-{method_name}.txt")
    if logcat_path and logcat_path.exists():
        lines = logcat_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        interesting = [
            line.rstrip()
            for line in lines
            if any(
                marker in line
                for marker in (
                    "FATAL EXCEPTION",
                    "AndroidRuntime",
                    "NoSuchMethodError",
                    "IllegalStateException",
                    "SecurityException",
                    "Process crashed",
                    "Caused by",
                )
            )
        ]
        if interesting:
            snippets.append("Logcat:\n" + "\n".join(interesting[-12:]))

    testlog_path = find_latest_android_artifact("testlog", "test-results.log")
    if testlog_path and testlog_path.exists():
        text = testlog_path.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            snippets.append("Instrumentation:\n" + tail_output(text, limit=8))

    return "\n\n".join(snippets)


def run_backend_suite() -> Dict[str, Any]:
    result = run_command([sys.executable, "-m", "pytest", "-q", "local-backend/tests"])
    passed = result["exit_code"] == 0
    summary = "Pytest green" if passed else "Pytest нашел ошибки"
    for line in reversed(result["output"].splitlines()):
        if "passed" in line or "failed" in line or "error" in line.lower():
            summary = line.strip()
            break
    return {
        "status": "passed" if passed else "failed",
        "summary": summary,
        "exit_code": result["exit_code"],
        "duration_sec": result["duration_sec"],
        "output_tail": tail_output(result["output"]),
        "details": [],
    }


def run_android_quality_suite() -> Dict[str, Any]:
    result = run_command(["./gradlew", "test", "lint"])
    passed = result["exit_code"] == 0
    summary = "Gradle quality green" if passed else "Gradle quality failed"
    for line in reversed(result["output"].splitlines()):
        line = line.strip()
        if line.startswith("BUILD "):
            summary = line
            break
    return {
        "status": "passed" if passed else "failed",
        "summary": summary,
        "exit_code": result["exit_code"],
        "duration_sec": result["duration_sec"],
        "output_tail": tail_output(result["output"]),
        "details": [],
    }


def run_android_ui_suite() -> Dict[str, Any]:
    serial = resolve_android_serial()
    if not serial:
        return {
            "status": "failed",
            "summary": "Эмулятор не найден",
            "exit_code": 1,
            "duration_sec": 0.0,
            "output_tail": "Нужен запущенный Android emulator, чтобы прогнать UI smoke.",
            "details": [],
        }

    env = os.environ.copy()
    env["ANDROID_SERIAL"] = serial
    details = []
    started_at = time.monotonic()

    setup_commands = [
        [sys.executable, "local-backend/tools/seed_ui_test_data.py"],
    ]

    # If adb is not on PATH but ANDROID_SERIAL is forced, Gradle can still talk to the device.
    for command in setup_commands:
        if command[0] == "adb":
            continue
        setup_result = run_command(command, env=env)
        if setup_result["exit_code"] != 0:
            return {
                "status": "failed",
                "summary": "Не удалось подготовить UI-данные",
                "exit_code": setup_result["exit_code"],
                "duration_sec": time.monotonic() - started_at,
                "output_tail": tail_output(setup_result["output"]),
                "details": details,
            }

    emulator_prep = [
        ["wait-for-device"],
        ["shell", "settings", "put", "global", "window_animation_scale", "0"],
        ["shell", "settings", "put", "global", "transition_animation_scale", "0"],
        ["shell", "settings", "put", "global", "animator_duration_scale", "0"],
        ["shell", "wm", "dismiss-keyguard"],
    ]
    for adb_command in emulator_prep:
        adb_command = [find_adb() or "adb", "-s", serial, *adb_command]
        setup_result = run_command(adb_command, env=env)
        if setup_result["exit_code"] != 0:
            return {
                "status": "failed",
                "summary": "Не удалось подготовить эмулятор",
                "exit_code": setup_result["exit_code"],
                "duration_sec": time.monotonic() - started_at,
                "output_tail": tail_output(setup_result["output"]),
                "details": details,
            }

    for test_class, label in UI_TEST_CLASSES:
        command = [
            "./gradlew",
            "connectedDebugAndroidTest",
            f"-Pandroid.testInstrumentationRunnerArguments.class={test_class}",
        ]
        attempt_logs: List[str] = []
        result = None
        attempts = 2
        for attempt in range(1, attempts + 1):
            run_command([sys.executable, "local-backend/tools/seed_ui_test_data.py"], env=env)
            run_adb(serial, ["shell", "am", "force-stop", APP_PACKAGE], env=env)
            run_adb(serial, ["shell", "pm", "clear", APP_PACKAGE], env=env)
            run_adb(serial, ["logcat", "-c"], env=env)
            result = run_command(command, env=env)
            attempt_logs.append(
                f"Попытка {attempt}: exit={result['exit_code']}\n{tail_output(result['output'], limit=14)}"
            )
            if result["exit_code"] == 0:
                break
            time.sleep(2)

        assert result is not None
        failure_diagnostics = ""
        if result["exit_code"] != 0:
            failure_diagnostics = collect_android_failure_diagnostics(test_class)

        combined_output_tail = "\n\n".join(part for part in [*attempt_logs[-2:], failure_diagnostics] if part)
        item = {
            "label": label,
            "class": test_class,
            "status": "passed" if result["exit_code"] == 0 else "failed",
            "duration_sec": round(result["duration_sec"], 2),
            "attempts": 1 if result["exit_code"] == 0 and len(attempt_logs) == 1 else len(attempt_logs),
            "output_tail": combined_output_tail,
        }
        details.append(item)
        if result["exit_code"] != 0:
            return {
                "status": "failed",
                "summary": f"UI smoke упал на сценарии: {label}",
                "exit_code": result["exit_code"],
                "duration_sec": time.monotonic() - started_at,
                "output_tail": combined_output_tail,
                "details": details,
            }

    return {
        "status": "passed",
        "summary": f"UI smoke green: {len(details)}/{len(UI_TEST_CLASSES)} сценария",
        "exit_code": 0,
        "duration_sec": time.monotonic() - started_at,
        "output_tail": "\n".join(
            f"{item['label']}: {item['status']} ({item['duration_sec']}s, попыток {item['attempts']})" for item in details
        ),
        "details": details,
    }


def main():
    suites = normalize_requested_suites(sys.argv[1:])
    mark_run_started(suites, os.getpid())
    try:
        for suite in suites:
            if suite == "backend_api":
                command = f"{sys.executable} -m pytest -q local-backend/tests"
                runner = run_backend_suite
            elif suite == "android_quality":
                command = "./gradlew test lint"
                runner = run_android_quality_suite
            elif suite == "android_ui":
                command = "./gradlew connectedDebugAndroidTest (по одному UI-сценарию)"
                runner = run_android_ui_suite
            else:
                continue

            mark_suite_started(suite, command)
            result = runner()
            mark_suite_finished(suite, **result)
    finally:
        mark_run_finished()


if __name__ == "__main__":
    main()
