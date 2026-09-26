"""Tests for non-live zteClient runtime behavior."""

from __future__ import annotations

import base64
import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
import xml.etree.ElementTree as ET

from custom_components.zte_tracker.zteclient import zte_client as zte_client_module
from custom_components.zte_tracker.zteclient.zte_client import zteClient


def _request(url: str = "http://router/") -> SimpleNamespace:
    return SimpleNamespace(
        url=url,
        headers={
            "Cookie": "secret",
            "Authorization": "Bearer secret",
            "X-Test": "ok",
        },
    )


def _response(
    *,
    text: str = "",
    content: bytes | None = None,
    json_data=None,
    status_code: int = 200,
    request=None,
):
    response = MagicMock()
    response.text = text
    response.content = content if content is not None else text.encode("utf-8")
    response.status_code = status_code
    response.request = request or _request()
    response.raise_for_status = Mock()
    if json_data is not None:
        response.json = Mock(return_value=json_data)
    return response


def _make_client(model: str = "F6640", **kwargs) -> zteClient:
    return zteClient("192.168.1.1", "admin", "secret", model, **kwargs)


def test_init_resolves_scheme_models_and_profiles() -> None:
    """Model aliases and scheme defaults should stay stable."""
    https_client = _make_client("F6640")
    http_client = _make_client("F6640", scheme="http", verify_ssl=True)

    assert "F6640" in zteClient.get_models()
    assert https_client.base_url == "https://192.168.1.1"
    assert http_client.base_url == "http://192.168.1.1"
    assert http_client.verify_ssl is False
    profiles = zteClient.get_profiles()
    assert "F6640" in profiles
    assert "F8748" in profiles
    assert "H288A" in profiles


def test_setup_session_sets_headers_and_mesh_preflight() -> None:
    """Mesh topology should prime the session like a browser."""
    fake_session = MagicMock()
    fake_session.headers = {}
    fake_session.get = Mock()
    client = _make_client(mesh_topology=True)

    with patch.object(zte_client_module, "Session", return_value=fake_session):
        client._setup_session()

    assert client.session is fake_session
    assert fake_session.mount.call_count == 2
    assert fake_session.headers["DNT"] == "1"
    assert fake_session.headers["X-Requested-With"] == "XMLHttpRequest"
    fake_session.get.assert_called_once_with(
        "https://192.168.1.1/", verify=False, timeout=10
    )


def test_login_short_circuits_when_session_is_fresh() -> None:
    """A fresh login_data cache should avoid new HTTP work."""
    client = _make_client()
    client.session = object()
    client.login_data = {"login_need_refresh": 0}

    assert client.login() is True


def test_login_success_populates_state() -> None:
    """A complete challenge-response login should succeed."""
    client = _make_client()
    client._setup_session = Mock()
    client.session = MagicMock()
    client.get_session_token = Mock(return_value="session-token")
    client.session.get.return_value = _response(
        content=b"<ajax_response_xml_root>abc123</ajax_response_xml_root>"
    )
    client.session.post.return_value = _response(
        json_data={"login_need_refresh": 0, "lockingTime": 0}
    )

    assert client.login() is True
    assert client.statusmsg == "Login successful."
    assert client.login_data == {"login_need_refresh": 0, "lockingTime": 0}


@pytest.mark.parametrize(
    ("json_data", "message"),
    [
        (
            {"login_need_refresh": 0, "lockingTime": -1, "loginErrMsg": "locked"},
            "Router is locked: locked",
        ),
        (
            {"login_need_refresh": 0, "lockingTime": 30},
            "Router is locked for 30 seconds: Too many login errors.",
        ),
        (
            {"login_need_refresh": 0, "lockingTime": 0, "loginErrMsg": "Bad password"},
            "Login denied: Bad password",
        ),
    ],
)
def test_login_reports_router_side_failures(json_data, message) -> None:
    """Router login failures should surface a clear status message."""
    client = _make_client()
    client._setup_session = Mock()
    client.session = MagicMock()
    client.get_session_token = Mock(return_value="session-token")
    client.session.get.return_value = _response(
        content=b"<ajax_response_xml_root>abc123</ajax_response_xml_root>"
    )
    client.session.post.return_value = _response(json_data=json_data)

    assert client.login() is False
    assert client.statusmsg == message


def test_login_refreshes_mesh_sessions_and_handles_token_errors() -> None:
    """Mesh logins should refresh the landing page and report missing tokens."""
    client = _make_client(mesh_topology=True)
    client._setup_session = Mock()
    client.session = MagicMock()
    client.get_session_token = Mock(return_value="session-token")
    client.session.get.return_value = _response(
        content=b"<ajax_response_xml_root></ajax_response_xml_root>"
    )

    assert client.login() is False
    assert client.statusmsg == "Empty login_token received from router."

    client.session.get.return_value = _response(
        content=b"<ajax_response_xml_root>abc123</ajax_response_xml_root>"
    )
    client.session.post.return_value = _response(
        json_data={"login_need_refresh": 1, "lockingTime": 0}
    )
    assert client.login() is True
    assert client.session.get.call_count >= 2


def test_login_handles_get_session_token_connection_errors() -> None:
    """Connection errors during the first challenge step should be reported."""
    client = _make_client()
    client._setup_session = Mock()
    client.session = MagicMock()
    client.get_session_token = Mock(side_effect=requests.exceptions.ConnectionError())

    assert client.login() is False
    assert "Cannot connect to router" in client.statusmsg


def test_login_cleans_up_after_unexpected_outer_failure() -> None:
    """Unexpected failures should close the session and clear login data."""
    client = _make_client()
    client._setup_session = Mock(side_effect=RuntimeError("boom"))
    old_session = MagicMock()
    client.session = old_session
    client.login_data = {"old": True}

    assert client.login() is False
    assert client.login_data is None
    old_session.close.assert_called_once()


def test_get_session_token_validates_lock_and_presence() -> None:
    """Session token reads should reject locked or empty responses."""
    client = _make_client()

    with pytest.raises(RuntimeError):
        client.get_session_token()

    client.session = MagicMock()
    client.session.get.return_value = _response(
        json_data={"lockingTime": 0, "sess_token": "abc123"}
    )
    assert client.get_session_token() == "abc123"

    client.session.get.return_value = _response(json_data={"lockingTime": 1})
    with pytest.raises(ValueError):
        client.get_session_token()


def test_logout_handles_success_and_failure() -> None:
    """Logout should always clear session state."""
    client = _make_client()
    old_session = MagicMock()
    client.session = old_session
    client.login_data = {"ok": 1}

    client.logout()
    old_session.close.assert_called_once()
    assert client.session is None
    assert client.login_data is None

    old_session = MagicMock()
    client.session = old_session
    client.login_data = {"ok": 1}
    client.session.post.side_effect = RuntimeError("boom")
    client.logout()
    old_session.close.assert_called_once()
    assert client.session is None
    assert client.login_data is None


def test_get_devices_response_combines_sources_and_handles_errors() -> None:
    """Device aggregation should merge LAN and WLAN results safely."""
    client = _make_client()
    client.get_lan_devices = Mock(return_value=[{"MACAddress": "AA"}])
    client.get_wifi_devices = Mock(return_value=[{"MACAddress": "BB"}])
    assert client.get_devices_response() == [{"MACAddress": "AA"}, {"MACAddress": "BB"}]

    client.get_lan_devices = Mock(return_value=None)
    client.get_wifi_devices = Mock(return_value=None)
    assert client.get_devices_response() is None

    client.get_lan_devices = Mock(side_effect=RuntimeError("boom"))
    assert client.get_devices_response() is None


def test_get_lan_devices_uses_menu_view_and_reports_failures() -> None:
    """LAN fetches should prepare context before parsing devices."""
    client = _make_client()
    client.session = MagicMock()
    client.parse_devices = Mock(return_value=[{"MACAddress": "AA"}])
    client.session.get.side_effect = [_response(), _response(text="<xml/>")]

    assert client.get_lan_devices() == [{"MACAddress": "AA"}]
    assert client.statusmsg == "OK"
    client.parse_devices.assert_called_once_with("<xml/>", "OBJ_ACCESSDEV_ID", "LAN")

    client.session = None
    assert client.get_lan_devices() is None
    assert "Failed to get LAN devices" in client.statusmsg


def test_get_wifi_devices_tries_direct_then_falls_back() -> None:
    """WiFi fetches should retry with the setup request when needed."""
    client = _make_client()
    client.session = MagicMock()
    client.parse_devices = Mock(return_value=[{"MACAddress": "AA"}])
    client.session.get.side_effect = [
        RuntimeError("fail"),
        _response(),
        _response(text="<xml/>"),
    ]

    assert client.get_wifi_devices() == [{"MACAddress": "AA"}]
    assert client.statusmsg == "OK"

    client.session = None
    assert client.get_wifi_devices() is None
    assert "Failed to get WiFi devices" in client.statusmsg


def test_fetch_topology_inline_tracks_failures_and_success() -> None:
    """Inline topology fetches should update the circuit breaker state."""
    client = _make_client()
    client.session = MagicMock()
    client.get_guid = Mock(side_effect=[1, 2])
    client._parse_topology_json = Mock(return_value=[{"MACAddress": "AA"}])
    client.session.get.side_effect = [
        _response(),
        _response(text='{"ad":{"1":{"MacAddr":"aa"}}}'),
    ]

    result = client._fetch_topology_inline("topo_lua.lua", 0)
    assert result == [{"MACAddress": "AA"}]
    assert client._topo_failures == 0
    assert client.statusmsg == "OK"

    client._parse_topology_json.return_value = None
    client.get_guid = Mock(side_effect=[3, 4])
    client.session.get.side_effect = [
        _response(),
        _response(text="<html>timeout</html>"),
    ]
    assert client._fetch_topology_inline("topo_lua.lua", 1) is None
    assert client._topo_failures == 2

    client.get_guid = Mock(side_effect=[5, 6])
    client.session.get.side_effect = [_response(), _response(text="{not-json}")]
    assert client._fetch_topology_inline("topo_lua.lua", 2) is None
    assert client._topo_failures == 3


def test_get_router_details_respects_flag_and_errors() -> None:
    """Router details should be skippable and safe on parser failures."""
    client = _make_client(query_router_details=False)
    assert client.get_router_details() == {}

    client = _make_client()
    client.session = MagicMock()
    client.session.get.side_effect = [
        _response(),
        _response(
            text=(
                "<ajax_response_xml_root>"
                "<OBJ_CPUMEMUSAGE_ID><Instance>"
                "<ParaName>CpuUsage1</ParaName><ParaValue>7</ParaValue>"
                "</Instance></OBJ_CPUMEMUSAGE_ID>"
                "<OBJ_POWERONTIME_ID><Instance>"
                "<ParaName>PowerOnTime</ParaName><ParaValue>12</ParaValue>"
                "</Instance></OBJ_POWERONTIME_ID>"
                "<OBJ_DEVINFO_ID><Instance>"
                "<ParaName>ModelName</ParaName><ParaValue>F6600P</ParaValue>"
                "<ParaName>HardwareVer</ParaName><ParaValue>V2</ParaValue>"
                "<ParaName>SoftwareVer</ParaName><ParaValue>V1</ParaValue>"
                "<ParaName>ManuFacturer</ParaName><ParaValue>ZTE</ParaValue>"
                "</Instance></OBJ_DEVINFO_ID>"
                "</ajax_response_xml_root>"
            )
        ),
    ]
    details = client.get_router_details()
    assert details["CpuUsage1"] == 7
    assert details["PowerOnTime"] == 12
    assert details["ModelName"] == "F6600P"

    client.session.get.side_effect = RuntimeError("boom")
    assert client.get_router_details() is None


def test_fetch_wan_status_xml_and_error_paths() -> None:
    """WAN XML fetches should enforce router-side success markers."""
    client = _make_client()
    client.session = MagicMock()
    client.get_guid = Mock(side_effect=[1, 2])
    client.session.get.side_effect = [
        _response(),
        _response(
            text="<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR></ajax_response_xml_root>"
        ),
    ]

    xml = client._fetch_wan_status_xml()
    assert xml.tag == "ajax_response_xml_root"

    client.get_guid = Mock(side_effect=[3, 4])
    client.session.get.side_effect = [
        _response(),
        _response(
            text="<ajax_response_xml_root><IF_ERRORSTR>NOPE</IF_ERRORSTR></ajax_response_xml_root>"
        ),
    ]
    with pytest.raises(Exception, match="Router error: NOPE"):
        client._fetch_wan_status_xml()


def test_get_wan_status_handles_disabled_traffic_and_missing_instances() -> None:
    """WAN status should support disabled queries and F8748 traffic counters."""
    disabled = _make_client(query_wan_status=False)
    assert disabled.get_wan_status() == {}

    traffic_client = _make_client("F8748")
    traffic_client.get_pon_optical_info = Mock(return_value={"PON_rx_power_dbm": -18.0})
    traffic_client._fetch_wan_status_xml = Mock(
        return_value=ET.fromstring(
            "<ajax_response_xml_root>"
            "<ID_WAN_COMFIG><Instance>"
            "<ParaName>WANCName</ParaName><ParaValue>WAN_internet</ParaValue>"
            "<ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>"
            "</Instance><Instance>"
            "<ParaName>RxBytes</ParaName><ParaValue>12</ParaValue>"
            "<ParaName>TxBytes</ParaName><ParaValue>34</ParaValue>"
            "<ParaName>RxPackets</ParaName><ParaValue>56</ParaValue>"
            "<ParaName>TxPackets</ParaName><ParaValue>78</ParaValue>"
            "<ParaName>ErrorsReceived</ParaName><ParaValue>1</ParaValue>"
            "<ParaName>ErrorsSent</ParaName><ParaValue>2</ParaValue>"
            "</Instance></ID_WAN_COMFIG></ajax_response_xml_root>"
        )
    )
    attrs = traffic_client.get_wan_status()
    assert attrs["WAN_connected"] is True
    assert attrs["WAN_rx_bytes"] == 12
    assert attrs["WAN_tx_errors"] == 2
    assert attrs["PON_rx_power_dbm"] == -18.0

    traffic_client._fetch_wan_status_xml = Mock(
        return_value=ET.fromstring("<ajax_response_xml_root></ajax_response_xml_root>")
    )
    assert "WAN_status_error" in traffic_client.get_wan_status()


def test_get_pon_optical_info_reports_errors_as_empty() -> None:
    """Optical diagnostics should fail closed on router errors."""
    client = _make_client("F6600P")
    client.session = MagicMock()
    client.get_guid = Mock(side_effect=[1, 2])
    client.session.get.side_effect = [
        _response(),
        _response(
            text="<ajax_response_xml_root><IF_ERRORSTR>NOPE</IF_ERRORSTR></ajax_response_xml_root>"
        ),
    ]

    assert client.get_pon_optical_info() == {}


def test_log_request_filters_sensitive_headers() -> None:
    """Request logging should redact auth headers."""
    client = _make_client()
    response = _response(request=_request("https://router/test"))

    with patch.object(zte_client_module._LOGGER, "debug") as debug:
        client.log_request(response)

    safe_headers = debug.call_args.args[-1]
    assert "Cookie" not in safe_headers
    assert "Authorization" not in safe_headers
    assert safe_headers["X-Test"] == "ok"


def test_parse_devices_handles_common_router_shapes_and_errors() -> None:
    """Device parsing should normalize names, ports, and connection flags."""
    client = _make_client()
    xml = (
        "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
        "<OBJ_WLANAP_ID><Instance>"
        "<ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP1</ParaValue>"
        "<ParaName>ESSID</ParaName><ParaValue>MainWiFi</ParaValue>"
        "</Instance></OBJ_WLANAP_ID>"
        "<OBJ_WLAN_AD_ID>"
        "<Instance>"
        "<ParaName>MACAddress</ParaName><ParaValue>aa:bb</ParaValue>"
        "<ParaName>IPAddress</ParaName><ParaValue>10.0.0.2</ParaValue>"
        "<ParaName>HostName</ParaName><ParaValue>Phone</ParaValue>"
        "<ParaName>IconType</ParaName><ParaValue>smartphone</ParaValue>"
        "<ParaName>Active</ParaName><ParaValue>true</ParaValue>"
        "<ParaName>AliasName</ParaName><ParaValue>DEV.WIFI.AP1</ParaValue>"
        "<ParaName>ConnectTime</ParaName><ParaValue>2025/11/17 Mon 14:23:45</ParaValue>"
        "</Instance>"
        "<Instance><ParaName>MACAddress</ParaName><ParaValue></ParaValue></Instance>"
        "</OBJ_WLAN_AD_ID></ajax_response_xml_root>"
    )
    devices = client.parse_devices(xml)
    assert devices[0]["MACAddress"] == "AA:BB"
    assert devices[0]["Port"] == "MainWiFi"
    assert devices[0]["Active"] is True
    assert devices[0]["ConnectTime"] == "2025-11-17T14:23:45"

    assert client.parse_devices("") == []
    with pytest.raises(Exception, match="Invalid XML format"):
        client.parse_devices("<html></html>")
    with pytest.raises(Exception, match="Router error: BAD"):
        client.parse_devices(
            "<ajax_response_xml_root><IF_ERRORSTR>BAD</IF_ERRORSTR></ajax_response_xml_root>"
        )
    with pytest.raises(ET.ParseError):
        client.parse_devices("<ajax_response_xml_root>")


def test_reboot_covers_success_failure_and_header_shapes() -> None:
    """Reboot should compute the expected Check header variants."""
    client = _make_client()
    client.login = Mock(return_value=False)
    assert client.reboot() is False

    client = _make_client()
    client.login = Mock(return_value=True)
    client.get_session_token = Mock(return_value="TESTTOKEN")
    client.logout = Mock()
    client.session = MagicMock()
    client.session.get.return_value = _response()
    client.session.post.return_value = _response(
        content=b"<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR></ajax_response_xml_root>"
    )
    fake_ciphertext = b"ciphertext"
    fake_key = MagicMock()
    fake_key.encrypt.return_value = fake_ciphertext

    with patch.object(
        zte_client_module.serialization,
        "load_pem_public_key",
        return_value=fake_key,
    ):
        assert client.reboot() is True

    post_data = "IF_ACTION=Restart&Btn_restart=&_sessionTOKEN=TESTTOKEN"
    expected_digest = hashlib.sha256(post_data.encode("utf-8")).hexdigest()
    encrypted_input = fake_key.encrypt.call_args.args[0]
    assert encrypted_input == expected_digest.encode("utf-8")
    assert client.session.post.call_args.kwargs["headers"]["Check"] == base64.b64encode(
        fake_ciphertext
    ).decode("utf-8")

    unencrypted = _make_client("H2640")
    unencrypted.login = Mock(return_value=True)
    unencrypted.get_session_token = Mock(return_value="TESTTOKEN")
    unencrypted.logout = Mock()
    unencrypted.session = MagicMock()
    unencrypted.session.get.return_value = _response()
    unencrypted.session.post.return_value = _response(
        content=b"<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR></ajax_response_xml_root>"
    )
    assert unencrypted.reboot() is True
    assert (
        unencrypted.session.post.call_args.kwargs["headers"]["Check"] == expected_digest
    )

    failing = _make_client()
    failing.login = Mock(return_value=True)
    failing.get_session_token = Mock(return_value="")
    failing.logout = Mock()
    failing.session = MagicMock()
    failing.session.get.return_value = _response()
    assert failing.reboot() is False
