"""Tests for the ZTE E2633 (China Mobile firmware) login and WiFi client reading.

They run against a LOCAL FAKE router (tests/_fake_e2633.py) that only reproduces the
flow measured from a browser session. They prove the code follows that flow; they do
NOT prove a real E2633 accepts it.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import _fake_e2633 as fake

from custom_components.zte_tracker.zteclient.zte_client import zteClient


def _client(router, password: str = fake.PASSWORD) -> zteClient:
    return zteClient(router.host, fake.USERNAME, password, "E2633", scheme="http")


def test_login_and_read_wifi_clients(fake_e2633) -> None:
    c = _client(fake_e2633)
    assert c.login()
    devices = c.get_devices_response()
    assert fake_e2633.login_count == 1
    assert [d["MACAddress"] for d in devices] == [
        "02:00:00:00:00:01",
        "02:00:00:00:00:02",
    ]
    assert all(d["NetworkType"] == "WLAN" for d in devices)
    assert [d["Port"] for d in devices] == ["2.4G", "5G"]
    assert devices[0]["HostName"] == "host-a"
    assert [d["Rssi"] for d in devices] == [-65, -72]
    assert devices[1]["WirelessMode"] == "802.11ac"
    assert (devices[0]["RxRate"], devices[0]["TxRate"]) == (1200, 800)


def test_wrong_password_is_not_retried_and_not_leaked(fake_e2633) -> None:
    wrong_password = "wrong-password-used-only-in-this-test"
    c = _client(fake_e2633, wrong_password)
    assert not c.login()
    assert fake_e2633.login_count == 1
    assert wrong_password not in c.statusmsg
    # The router refused the credentials: back off, so the next call sends no login.
    assert not c.login()
    assert fake_e2633.login_count == 1


def test_expired_session_logs_in_again(fake_e2633) -> None:
    c = _client(fake_e2633)
    assert c.login()
    assert c.get_wifi_devices()
    fake_e2633.expire_sessions = 1
    assert c.get_wifi_devices() is None
    assert c.login_data is None
    assert c.login()
    assert fake_e2633.login_count == 2
    assert c.get_wifi_devices()


def test_reboot_wan_details_and_lan_are_unsupported(fake_e2633) -> None:
    c = _client(fake_e2633)
    assert c.login()
    assert not c.reboot()
    assert c.get_wan_status() == {}
    assert c.get_router_details() == {}
    assert c.get_lan_devices() == []


def test_model_is_registered() -> None:
    assert "E2633" in zteClient.get_models()


# --- review point 2: a failed read is an error, not "no devices" -------------------


def test_failed_wifi_read_is_an_error_not_an_empty_list(fake_e2633) -> None:
    """get_devices_response used to return [] when the WiFi read failed, so every
    tracked device went away while the router was still connected."""
    c = _client(fake_e2633)
    assert c.login()
    fake_e2633.data_status = 503
    assert c.get_devices_response() is None
    assert "WiFi" in c.statusmsg


def test_expired_session_read_is_an_error_not_an_empty_list(fake_e2633) -> None:
    c = _client(fake_e2633)
    assert c.login()
    fake_e2633.expire_sessions = 1
    assert c.get_devices_response() is None


def test_router_with_no_wifi_clients_is_an_empty_list(fake_e2633) -> None:
    """A successful read of an empty list is still an empty list."""
    fake_e2633.clients = {"clientsData": {"MGET_INST_NUM": 0}}
    c = _client(fake_e2633)
    assert c.login()
    assert c.get_devices_response() == []


# --- review point 3: logout, backoff, HTTP status ----------------------------------


def test_logout_drops_the_session(fake_e2633) -> None:
    c = _client(fake_e2633)
    assert c.login()
    session = c.session
    with patch.object(session, "close", wraps=session.close) as closed:
        c.logout()
    closed.assert_called_once()
    assert c.session is None
    assert c.login_data is None
    # The next login starts a new session.
    assert c.login()
    assert fake_e2633.login_count == 2


def test_network_loss_does_not_start_the_long_backoff(fake_e2633) -> None:
    c = _client(fake_e2633)
    fake_e2633.stop()
    assert not c.login()
    assert fake_e2633.login_count == 0
    fake_e2633.start()  # the router is back: the very next login must be tried
    assert c.login()
    assert fake_e2633.login_count == 1


# 503 is retried by the session adapter and raised as RetryError; 404 reaches raise_for_status.
@pytest.mark.parametrize("status", [503, 404])
@pytest.mark.parametrize("page", ["home_status", "token_status"])
def test_http_error_before_the_login_post_sends_no_credentials(
    fake_e2633, page, status
) -> None:
    """An HTTP error on the login or token page must not lead to the credential POST,
    and it is not a refusal, so it must not back off either."""
    c = _client(fake_e2633)
    setattr(fake_e2633, page, status)
    assert not c.login()
    assert fake_e2633.login_count == 0
    assert str(status) in c.statusmsg
    setattr(fake_e2633, page, 200)
    assert c.login()
    assert fake_e2633.login_count == 1


@pytest.mark.parametrize("status", [503, 404])
def test_http_error_on_the_check_read_after_login_is_not_a_refusal(
    fake_e2633, status
) -> None:
    c = _client(fake_e2633)
    fake_e2633.data_status = status
    assert not c.login()
    assert fake_e2633.login_count == 1
    fake_e2633.data_status = 200
    assert c.login()  # no backoff: tried again at once
    assert fake_e2633.login_count == 2


def test_refused_login_backs_off_then_recovers_after_the_pause(fake_e2633) -> None:
    c = _client(fake_e2633, "wrong-password-used-only-in-this-test")
    assert not c.login()
    assert not c.login()
    assert fake_e2633.login_count == 1
    assert "paused" in c.statusmsg.lower()
    # Once the pause has run out the client tries again.
    c._cmcc_paused_until = 0.0
    assert not c.login()
    assert fake_e2633.login_count == 2
