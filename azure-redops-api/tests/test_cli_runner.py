"""Tests for cli_runner + output_parser + webserver_manager integration."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services import cli_runner, output_parser, webserver_manager
from app.services.cli_runner import (
    FLAG_ALIASES, INTERACTIVE_ACTIVITIES, VALID_ACTIVITIES,
    _build_argv, list_activities, run_activity,
)
from app.config import AZURE_REDOPS_SCRIPT, TEST_MODE


# ---------- argv construction ----------------------------------------------

def test_build_argv_known_activity():
    argv = _build_argv("self", {"u": "alice@contoso.com", "tid": "common"})
    assert "python" in argv[0].lower() or "python" in str(argv[0]).lower()
    assert str(AZURE_REDOPS_SCRIPT) in argv
    assert "-a" in argv and "self" in argv
    assert "-u" in argv and "alice@contoso.com" in argv
    assert "-tid" in argv and "common" in argv


def test_build_argv_unknown_activity_rejected():
    with pytest.raises(ValueError):
        _build_argv("bogus", {})


def test_build_argv_skips_empty_flags():
    argv = _build_argv("self", {"u": "", "p": None, "beta": False})
    assert "-u" not in argv and "-p" not in argv and "-beta" not in argv


def test_build_argv_boolean_flag_true():
    argv = _build_argv("list-users", {"debug": True})
    assert "-d" in argv


def test_build_argv_boolean_flag_false_omitted():
    argv = _build_argv("list-users", {"debug": False})
    assert "-d" not in argv


@pytest.mark.parametrize("key,cli", [
    ("username", "-u"), ("user", "-u"), ("upn", "-u"), ("u", "-u"),
    ("password", "-p"), ("pass", "-p"), ("p", "-p"),
    ("tenant_id", "-tid"), ("tid", "-tid"), ("tenant", "-tid"), ("t", "-tid"),
    ("load", "-l"), ("l", "-l"),
    ("save", "-s"), ("s", "-s"),
    ("name", "-n"), ("n", "-n"),
    ("json", "-j"), ("j", "-j"),
    ("filter", "-fl"), ("fl", "-fl"),
    ("file_path", "-fp"), ("fp", "-fp"),
    ("code_path", "-cp"), ("cp", "-cp"),
    ("verify", "-v"), ("v", "-v"),
    ("refresh", "-r"), ("r", "-r"),
    ("beta", "-beta"),
    ("record", "-re"), ("re", "-re"),
    ("scope", "-sc"), ("sc", "-sc"),
    ("debug", "-d"), ("d", "-d"),
    ("doubledebug", "-dd"), ("dd", "-dd"),
])
def test_flag_aliases_complete(key, cli):
    assert FLAG_ALIASES[key] == cli


# ---------- activity coverage ----------------------------------------------

@pytest.mark.parametrize("activity", sorted(VALID_ACTIVITIES))
def test_every_activity_is_known(activity):
    argv = _build_argv(activity, {})
    assert activity in argv


def test_count_activities_matches_readme():
    assert len(VALID_ACTIVITIES) == 24


def test_list_activities_sorted():
    out = list_activities()
    assert out == sorted(out)


def test_interactive_activities_subset():
    for a in INTERACTIVE_ACTIVITIES:
        assert a in VALID_ACTIVITIES


# ---------- run_activity: input validation ---------------------------------

def test_run_activity_unknown_returns_error():
    out = run_activity("totally-bogus", {})
    assert out["ok"] is False
    assert "Unknown activity" in out["stderr"]


# ---------- run_activity: mock path ---------------------------------------

def test_run_activity_mock_list_users_returns_json():
    out = run_activity("list-users", {})
    assert out["ok"] is True
    assert out["test_mode"] is True
    body = json.loads(out["stdout"])
    assert "value" in body
    assert isinstance(body["value"], list)


def test_run_activity_mock_phish_start_emits_device_code():
    out = run_activity("phish-start", {})
    assert out["ok"] is True
    assert out["test_mode"] is True
    assert out["user_code"].startswith("MOCK")
    assert out["verification_url"].startswith("https://")


def test_run_activity_mock_self_includes_tenant():
    out = run_activity("self", {"tid": "11111111-2222-3333-4444-555555555555"})
    body = json.loads(out["stdout"])
    assert body["tenantId"].startswith("11111111-2222-3333-4444-555555555555")


def test_run_activity_mock_gather_all_has_every_entity():
    out = run_activity("gather-all", {})
    body = json.loads(out["stdout"])
    for key in ("users", "groups", "applications",
                "servicePrincipals", "directoryRoles",
                "conditionalAccessPolicies"):
        assert key in body


def test_run_activity_mock_list_returns_activities():
    out = run_activity("list", {})
    for activity in VALID_ACTIVITIES:
        assert activity in out["stdout"]


def test_run_activity_mock_spray_returns_buckets():
    out = run_activity("spray", {})
    for key in ("valid", "invalid", "locked"):
        assert key in out


# ---------- run_activity: real path with mocked subprocess ----------------

def test_real_path_invokes_subprocess_when_present():
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "real-cli-output"
    fake_proc.stderr = ""
    with patch.object(cli_runner, "AZURE_REDOPS_PRESENT", True), \
         patch.object(cli_runner, "TEST_MODE", False), \
         patch.object(cli_runner.subprocess, "run", return_value=fake_proc) as run_mock:
        out = run_activity("list-users", {"u": "alice@x.com"})
        run_mock.assert_called_once()
        argv = run_mock.call_args.args[0]
        assert "list-users" in argv
        assert "-u" in argv
    assert out["stdout"] == "real-cli-output"
    assert out["ok"] is True
    assert out["test_mode"] is False


def test_real_path_timeout():
    import subprocess as real_sp
    fake = real_sp.TimeoutExpired(cmd=["x"], timeout=1, output="partial", stderr="err")
    fake.stdout = b"partial"
    fake.stderr = b"err"
    with patch.object(cli_runner, "AZURE_REDOPS_PRESENT", True), \
         patch.object(cli_runner, "TEST_MODE", False), \
         patch.object(cli_runner.subprocess, "run", side_effect=fake):
        out = run_activity("list-users", {})
    assert out["ok"] is False
    assert out["error"] == "timeout"


def test_real_path_missing_python():
    with patch.object(cli_runner, "AZURE_REDOPS_PRESENT", True), \
         patch.object(cli_runner, "TEST_MODE", False), \
         patch.object(cli_runner.subprocess, "run",
                       side_effect=FileNotFoundError("no python")):
        out = run_activity("list-users", {})
    assert out["ok"] is False
    assert out["error"] == "file_not_found"


# ---------- output_parser integration -------------------------------------

def test_parse_stdout_extracts_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.signature"
    stdout = f"Bearer {jwt}\naccess_token: {jwt}\n"
    parsed = output_parser.parse_stdout(stdout)
    assert jwt in parsed["tokens"]
    assert parsed["access_token"] == jwt


def test_parse_stdout_extracts_emails_and_tenant():
    tid = "11111111-2222-3333-4444-555555555555"
    stdout = f"TenantId: {tid}\nUser: alice@contoso.com\nbob@fabrikam.com\n"
    parsed = output_parser.parse_stdout(stdout)
    assert tid in parsed["tenant_ids"]
    assert "alice@contoso.com" in parsed["emails"]
    assert "bob@fabrikam.com" in parsed["emails"]


def test_parse_stdout_extracts_json_object():
    blob = json.dumps({"value": [{"id": "abc"}]})
    parsed = output_parser.parse_stdout("some preamble\n" + blob + "\n")
    assert any(isinstance(o, dict) and "value" in o for o in parsed["json_objects"])


def test_extract_users_filters_unique():
    p = output_parser.parse_stdout(json.dumps({"value": [
        {"id": "1", "displayName": "A", "userPrincipalName": "a@x"},
        {"id": "1", "displayName": "A-dup", "userPrincipalName": "a@x"},
        {"id": "2", "displayName": "B", "userPrincipalName": "b@x"},
    ]}))
    users = output_parser.extract_users(p)
    assert len(users) == 2
    assert [u["id"] for u in users] == ["1", "2"]


def test_extract_applications_dedupes():
    p = output_parser.parse_stdout(json.dumps({"value": [
        {"appId": "a1", "displayName": "X"},
        {"appId": "a1", "displayName": "Y"},
        {"appId": "a2", "displayName": "Z"},
    ]}))
    apps = output_parser.extract_applications(p)
    assert len(apps) == 2


def test_extract_phish_capture_pulls_tokens():
    p = output_parser.parse_stdout(json.dumps({
        "access_token": "AT", "refresh_token": "RT",
        "id_token": "IT", "expires_in": 3600,
        "userPrincipalName": "x@y", "tid": "11111111-2222-3333-4444-555555555555",
    }))
    cap = output_parser.extract_phish_capture(p)
    assert cap["access_token"] == "AT"
    assert cap["refresh_token"] == "RT"
    assert cap["id_token"] == "IT"
    assert cap["expires_in"] == 3600
    assert cap["tenant_id"].startswith("11111111-")


def test_parse_spray_result_buckets():
    p = output_parser.parse_stdout(
        "alice@x.com - Successful\n"
        "bob@x.com - Account Locked\n"
        "carol@x.com - Wrong password\n"
    )
    res = output_parser.parse_spray_result(p)
    assert len(res["valid"]) == 1
    assert len(res["locked"]) == 1
    assert len(res["invalid"]) == 1


def test_strip_ansi_removes_colors():
    assert output_parser.strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_partition_tokens_separates_id():
    real_id = ("eyJhbGciOiJIUzI1NiJ9."
               "eyJ3aWRzIjpbInIxIl0sInR5cCI6IklEIn0."
               "sig")
    real_at = ("eyJhbGciOiJIUzI1NiJ9."
               "eyJzdWIiOiIxIn0."
               "sig")
    out = output_parser.partition_tokens([real_id, real_at])
    assert real_id in out["id_tokens"]
    assert real_at in out["access_tokens"]


def test_dispatcher_attaches_users():
    result = {"stdout": json.dumps({"value": [
        {"id": "1", "userPrincipalName": "a@x", "displayName": "A"}
    ]})}
    out = output_parser.parse("list-users", result)
    assert "users" in out
    assert out["users"][0]["userPrincipalName"] == "a@x"
    assert "errors" in out
    assert "summary" in out


def test_dispatcher_attaches_capture():
    result = {"stdout": json.dumps({
        "access_token": "AT", "refresh_token": "RT",
        "userPrincipalName": "x@y",
    })}
    out = output_parser.parse("phish-capture", result)
    assert "capture" in out
    assert out["capture"]["access_token"] == "AT"


# ---------- webserver_manager ---------------------------------------------

def test_webserver_status_shape():
    s = webserver_manager.status()
    for key in ("running", "pid", "host", "port", "log",
                "started_at", "webserver_present",
                "cert_present", "test_mode"):
        assert key in s


def test_webserver_start_mock_when_script_missing():
    s0 = webserver_manager.status()
    if s0["webserver_present"]:
        pytest.skip("Webserver.py is present; mocking no-cert path")
    out = webserver_manager.start()
    assert out["ok"] is True
    assert out["test_mode"] is True


def test_webserver_stop_when_not_running():
    out = webserver_manager.stop()
    assert out["ok"] is True


def test_data_files_present_keys():
    info = cli_runner.data_files_present()
    for key in ("AzureRedOps.py", "Webserver.py", "apps.json",
                "auth_apps.json", "spray_all.json",
                "cert.pem", "key.pem"):
        assert key in info