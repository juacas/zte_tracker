"""Tests for scripts/redact_log.py (fake values only)."""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "redact_log", Path(__file__).resolve().parents[1] / "scripts" / "redact_log.py"
)
redact_log = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(redact_log)

SHA256 = "a" * 64
LOG = "\n".join(
    [
        "2026-10-19 10:00:00 DEBUG (SyncWorker_1) [x] Request 200 URL: http://192.0.2.1/ Headers: {'User-Agent': 'Mozilla/5.0', 'Cookie': 'SID=sidvalue123', 'Check': '" + SHA256 + "'}",
        "login body: Username=admin&Password=" + SHA256 + "&action=login&Frm_Logintoken=&captchaCode=&_sessionTOKEN=98765",
        'page: addParameter("_sessionTOKEN", "98765"); addParameter("Frm_Logintoken", "5551234");',
        "Set-Cookie: SID=sidvalue123; Path=/; HttpOnly",
        "Cookie: SID=sidvalue123",
        'json: {"Password": "plain-secret", "HostName": "my-phone", "Rssi": "-65", "token": 12345}',
        "client 02:00:00:00:00:01 (ip 192.0.2.10) joined; again 02-00-00-00-00-01 and 02:00:00:00:00:AA at 192.0.2.10",
        "router firmware V1.0.4 on Home Assistant 2026.1.0, version 1.2.3",
    ]
)
SECRETS = ["sidvalue123", "plain-secret", "my-phone", "98765", "5551234", "12345", SHA256, "admin"]


def _run(text: str) -> str:
    out = io.StringIO()
    redact_log.redact(io.StringIO(text), out)
    return out.getvalue()


def test_no_secret_value_survives() -> None:
    result = _run(LOG)
    for secret in SECRETS:
        assert secret not in result, secret
    assert "02:00:00:00:00:01" not in result.lower()
    assert "192.0.2." not in result


def test_same_mac_and_ip_get_the_same_placeholder() -> None:
    result = _run(LOG)
    assert result.count("<MAC-1>") == 2  # colon form and dash form of the same address
    assert result.count("<MAC-2>") == 1
    assert result.count("<IP-1>") == 1  # 192.0.2.1
    assert result.count("<IP-2>") == 2  # 192.0.2.10, twice


def test_versions_and_non_secret_text_are_kept() -> None:
    result = _run(LOG)
    assert "V1.0.4" in result and "2026.1.0" in result and "1.2.3" in result
    assert "Rssi" in result and "-65" in result
    assert "Request 200 URL" in result


def test_redaction_is_idempotent() -> None:
    once = _run(LOG)
    assert _run(once) == once


@pytest.mark.parametrize("line", ["", "plain line without anything\n"])
def test_clean_lines_are_unchanged(line) -> None:
    assert _run(line) == line


def test_main_reads_a_file_and_writes_an_output_file(tmp_path, capsys) -> None:
    source = tmp_path / "in.log"
    target = tmp_path / "out.log"
    source.write_text(LOG, encoding="utf-8")
    assert redact_log.main([str(source), "-o", str(target)]) == 0
    assert "plain-secret" not in target.read_text(encoding="utf-8")
    assert "Read the result" in capsys.readouterr().err
