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


EXTRA_LOG = "\n".join(
    [
        "cisco style 0200.0000.0001 and bare 020000000002 and upper 0200000000AB seen",
        "ipv6 2001:db8::1 and fe80::1%eth0 and full 2001:0db8:0000:0000:0000:0000:0000:0002 here",
        "Login failed: admin@router.home.lan and mail me@example.org",
        "Request 200 URL: https://router.home.lan:8443/getpage.lua?x=1 and http://user:pw1234@nas.local/ end",
        "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "2026-10-19 10:00:00.123 DEBUG at 10:00:01 build 1.2.3.4",
    ]
)


def test_more_address_forms_are_masked() -> None:
    result = _run(EXTRA_LOG)
    for leaked in (
        "0200.0000.0001", "020000000002", "0200000000AB", "2001:db8::1", "fe80::1", "2001:0db8",
        "router.home.lan", "admin@", "me@example.org", "nas.local", "pw1234", "user:",
    ):
        assert leaked not in result, leaked


def test_browser_versions_and_timestamps_are_not_mangled() -> None:
    result = _run(EXTRA_LOG)
    assert "Chrome/120.0.0.0" in result
    assert "Safari/537.36" in result
    assert "2026-10-19 10:00:00.123 DEBUG at 10:00:01" in result
    assert "https://<host>:8443/getpage.lua?x=1" in result
    assert "<IP-1>" in result  # build 1.2.3.4 is still an IPv4-shaped value


def test_the_same_mac_in_different_notations_gets_one_placeholder() -> None:
    result = _run("a 02:00:00:00:00:01 b 0200.0000.0001 c 020000000001 d 02-00-00-00-00-01")
    assert result.count("<MAC-1>") == 4 and "<MAC-2>" not in result
