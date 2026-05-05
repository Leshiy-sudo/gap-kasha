import importlib.util
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = BACKEND_DIR / "tools" / "run_admin_tests.py"
SPEC = importlib.util.spec_from_file_location("run_admin_tests_module", MODULE_PATH)
run_admin_tests = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(run_admin_tests)


def test_collect_android_failure_diagnostics_extracts_logcat_and_instrumentation(monkeypatch, tmp_path):
    device_dir = tmp_path / "emulator-5554"
    testlog_dir = device_dir / "testlog"
    testlog_dir.mkdir(parents=True)

    (device_dir / "logcat-com.gapkassa.LoginUiTest-passwordLoginWorks.txt").write_text(
        "\n".join(
            [
                "04-16 17:44:31.785 E AndroidXTracer: java.lang.NoSuchMethodError: missing",
                "04-16 17:44:31.835 I AndroidRuntime: VM exiting with result code 0.",
            ]
        ),
        encoding="utf-8",
    )
    (testlog_dir / "test-results.log").write_text(
        "INSTRUMENTATION_RESULT: shortMsg=Process crashed.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(run_admin_tests, "ANDROID_TEST_RESULTS_DIR", tmp_path)

    result = run_admin_tests.collect_android_failure_diagnostics(
        "com.gapkassa.LoginUiTest#passwordLoginWorks"
    )

    assert "NoSuchMethodError" in result
    assert "Process crashed" in result
