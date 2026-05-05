import base64
import sys


def admin_headers():
    token = base64.b64encode(b"admin:admin").decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_admin_autotest_status_endpoint_returns_default_snapshot(app_ctx):
    response = app_ctx["client"].get("/admin/api/tests", headers=admin_headers())

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["is_running"] is False
    assert set(payload["suites"].keys()) == {"backend_api", "android_quality", "android_ui"}
    assert payload["summary"]["total"] == 3


def test_admin_autotest_run_endpoint_delegates_to_runner(app_ctx, monkeypatch):
    captured = {}

    def fake_start_background_run(suites, actor_id):
        captured["suites"] = suites
        captured["actor_id"] = actor_id
        return {
            "is_running": True,
            "summary": {"headline": "Ок: 0 из 3, ошибок: 0, в очереди/работе: 1"},
            "suites": {},
        }

    monkeypatch.setattr(sys.modules["admin_panel"], "start_background_run", fake_start_background_run)

    response = app_ctx["client"].post(
        "/admin/api/tests/run",
        headers=admin_headers(),
        json={"suites": ["android_ui"]},
    )

    assert response.status_code == 200, response.text
    assert captured == {"suites": ["android_ui"], "actor_id": "admin"}
    assert response.json()["message"] == "autotests_started"


def test_admin_autotest_stop_endpoint_returns_updated_status(app_ctx, monkeypatch):
    monkeypatch.setattr(
        sys.modules["admin_panel"],
        "stop_background_run",
        lambda: {
            "is_running": False,
            "summary": {"headline": "Ок: 2 из 3, ошибок: 1, в очереди/работе: 0"},
            "suites": {},
        },
    )

    response = app_ctx["client"].post("/admin/api/tests/stop", headers=admin_headers())

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "autotests_stopped"
    assert response.json()["status"]["is_running"] is False
