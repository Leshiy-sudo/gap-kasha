import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from db import BASE_DIR, now_iso

REPO_ROOT = BASE_DIR.parent
STATUS_PATH = Path(
    os.getenv("AUTOTEST_STATUS_PATH", str(BASE_DIR / "data" / "autotest_status.json"))
).expanduser()
RUNNER_SCRIPT = BASE_DIR / "tools" / "run_admin_tests.py"

SUITES: Dict[str, Dict[str, str]] = {
    "backend_api": {
        "label": "Backend/API/security",
        "description": "Pytest по backend, API, БД, валидации и security-набору.",
    },
    "android_quality": {
        "label": "Android unit + lint",
        "description": "Gradle unit tests и lint-проверка Android-приложения.",
    },
    "android_ui": {
        "label": "Android UI smoke",
        "description": "Логин, создание комнаты, удаление комнаты и оффлайн-старт на эмуляторе.",
    },
}
SUITE_ORDER = list(SUITES.keys())
STATUS_VALUES = {"idle", "queued", "running", "passed", "failed", "cancelled"}
UI_TEST_CLASSES: List[Tuple[str, str]] = [
    ("com.gapkassa.LoginUiTest#passwordLoginWorks", "Логин"),
    ("com.gapkassa.CreateRoomUiTest#createRoomFromUiWorks", "Создание комнаты"),
    ("com.gapkassa.DeleteRoomUiTest#deleteRoomFromUiWorks", "Удаление комнаты"),
    ("com.gapkassa.OfflineStartUiTest#authorizedUserKeepsAccessOfflineAfterRecreate", "Оффлайн-старт"),
]


def _ensure_parent_dir():
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _default_suite_state(key: str) -> Dict[str, Any]:
    config = SUITES[key]
    return {
        "key": key,
        "label": config["label"],
        "description": config["description"],
        "status": "idle",
        "summary": "Еще не запускалось",
        "last_started_at": None,
        "last_finished_at": None,
        "duration_sec": None,
        "exit_code": None,
        "command": None,
        "output_tail": "",
        "details": [],
    }


def _default_state() -> Dict[str, Any]:
    suites = {key: _default_suite_state(key) for key in SUITE_ORDER}
    return {
        "generated_at": now_iso(),
        "is_running": False,
        "runner_pid": None,
        "current_suite": None,
        "summary": {
            "passed": 0,
            "failed": 0,
            "running": 0,
            "queued": 0,
            "idle": len(SUITE_ORDER),
            "cancelled": 0,
            "total": len(SUITE_ORDER),
            "headline": "Автотесты еще не запускались",
        },
        "suites": suites,
    }


def _normalize_suite_state(state: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _default_state()
    normalized.update({key: value for key, value in state.items() if key != "suites"})
    raw_suites = state.get("suites", {})
    for key in SUITE_ORDER:
        suite_state = _default_suite_state(key)
        suite_state.update(raw_suites.get(key, {}))
        if suite_state.get("status") not in STATUS_VALUES:
            suite_state["status"] = "idle"
        normalized["suites"][key] = suite_state
    normalized["summary"] = build_summary(normalized)
    normalized["generated_at"] = state.get("generated_at") or now_iso()
    return normalized


def load_status() -> Dict[str, Any]:
    if not STATUS_PATH.exists():
        return _default_state()
    try:
        state = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_state()
    normalized = _normalize_suite_state(state)
    if normalized.get("is_running") and not _is_runner_alive(normalized.get("runner_pid")):
        normalized["is_running"] = False
        normalized["runner_pid"] = None
        if normalized.get("current_suite"):
            current_key = normalized["current_suite"]
            suite = normalized["suites"].get(current_key)
            if suite and suite["status"] == "running":
                suite["status"] = "failed"
                suite["summary"] = suite.get("summary") or "Фоновый прогон прервался"
                suite["last_finished_at"] = now_iso()
        normalized["current_suite"] = None
        save_status(normalized)
    return normalized


def save_status(state: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_parent_dir()
    normalized = _normalize_suite_state(state)
    normalized["generated_at"] = now_iso()
    tmp_path = STATUS_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(STATUS_PATH)
    return normalized


def build_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    counts = {key: 0 for key in ("passed", "failed", "running", "queued", "idle", "cancelled")}
    for suite in state.get("suites", {}).values():
        status = suite.get("status", "idle")
        counts[status] = counts.get(status, 0) + 1
    total = len(state.get("suites", {})) or len(SUITE_ORDER)
    headline = (
        f"Ок: {counts['passed']} из {total}, "
        f"ошибок: {counts['failed']}, "
        f"в очереди/работе: {counts['queued'] + counts['running']}"
    )
    return {**counts, "total": total, "headline": headline}


def _is_runner_alive(pid: Any) -> bool:
    try:
        pid_value = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_value <= 0:
        return False
    try:
        os.kill(pid_value, 0)
    except OSError:
        return False
    return True


def normalize_requested_suites(suites: Optional[List[str]]) -> List[str]:
    if not suites:
        return SUITE_ORDER.copy()
    normalized: List[str] = []
    for suite in suites:
        if suite == "all":
            return SUITE_ORDER.copy()
        if suite in SUITES and suite not in normalized:
            normalized.append(suite)
    return normalized or SUITE_ORDER.copy()


def start_background_run(suites: Optional[List[str]], actor_id: str = "admin") -> Dict[str, Any]:
    requested = normalize_requested_suites(suites)
    state = load_status()
    if state.get("is_running") and _is_runner_alive(state.get("runner_pid")):
        raise RuntimeError("autotests_already_running")

    process = subprocess.Popen(
        [sys.executable, str(RUNNER_SCRIPT), *requested],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for key in SUITE_ORDER:
        suite = state["suites"][key]
        if key in requested:
            suite.update(
                {
                    "status": "queued",
                    "summary": f"Ожидает запуска ({actor_id})",
                    "last_started_at": None,
                    "last_finished_at": None,
                    "duration_sec": None,
                    "exit_code": None,
                    "output_tail": "",
                    "details": [],
                }
            )
    state["is_running"] = True
    state["runner_pid"] = process.pid
    state["current_suite"] = None
    return save_status(state)


def stop_background_run() -> Dict[str, Any]:
    state = load_status()
    pid = state.get("runner_pid")
    if not state.get("is_running") or not _is_runner_alive(pid):
        state["is_running"] = False
        state["runner_pid"] = None
        state["current_suite"] = None
        return save_status(state)

    try:
        os.killpg(int(pid), signal.SIGTERM)
    except ProcessLookupError:
        pass

    for suite in state["suites"].values():
        if suite["status"] in {"queued", "running"}:
            suite["status"] = "cancelled"
            suite["summary"] = "Прогон остановлен вручную"
            suite["last_finished_at"] = now_iso()
    state["is_running"] = False
    state["runner_pid"] = None
    state["current_suite"] = None
    return save_status(state)


def mark_run_started(suites: List[str], pid: int):
    state = load_status()
    state["is_running"] = True
    state["runner_pid"] = pid
    state["current_suite"] = None
    for key in suites:
        suite = state["suites"][key]
        suite["status"] = "queued"
        suite["summary"] = "Ожидает запуска"
        suite["output_tail"] = ""
        suite["details"] = []
    save_status(state)


def mark_suite_started(key: str, command: str):
    state = load_status()
    suite = state["suites"][key]
    suite["status"] = "running"
    suite["summary"] = "Идет прогон"
    suite["last_started_at"] = now_iso()
    suite["last_finished_at"] = None
    suite["duration_sec"] = None
    suite["exit_code"] = None
    suite["command"] = command
    suite["output_tail"] = ""
    suite["details"] = []
    state["current_suite"] = key
    save_status(state)


def mark_suite_finished(
    key: str,
    *,
    status: str,
    summary: str,
    exit_code: Optional[int],
    duration_sec: Optional[float],
    output_tail: str,
    details: Optional[List[Dict[str, Any]]] = None,
):
    state = load_status()
    suite = state["suites"][key]
    suite["status"] = status if status in STATUS_VALUES else "failed"
    suite["summary"] = summary
    suite["last_finished_at"] = now_iso()
    suite["duration_sec"] = round(duration_sec or 0.0, 2)
    suite["exit_code"] = exit_code
    suite["output_tail"] = output_tail
    suite["details"] = details or []
    if state.get("current_suite") == key:
        state["current_suite"] = None
    save_status(state)


def mark_run_finished():
    state = load_status()
    state["is_running"] = False
    state["runner_pid"] = None
    state["current_suite"] = None
    save_status(state)


def find_adb() -> Optional[str]:
    direct = os.getenv("ADB_PATH")
    if direct and Path(direct).exists():
        return direct
    for env_key in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        root = os.getenv(env_key)
        if root:
            candidate = Path(root) / "platform-tools" / "adb"
            if candidate.exists():
                return str(candidate)
    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb
    home_candidate = Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb"
    if home_candidate.exists():
        return str(home_candidate)
    return None


def resolve_android_serial() -> Optional[str]:
    forced = os.getenv("ANDROID_SERIAL")
    if forced:
        return forced
    adb = find_adb()
    if not adb:
        return None
    result = subprocess.run([adb, "devices"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "\tdevice" not in line:
            continue
        serial = line.split("\t", 1)[0].strip()
        if serial.startswith("emulator-"):
            return serial
    return None


def tail_output(text: str, limit: int = 30) -> str:
    lines = [line.rstrip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-limit:])
