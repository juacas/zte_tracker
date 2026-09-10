"""Unit tests for the diagnostics platform."""

import asyncio
import json
import os
import sys
import tempfile
import types
from unittest import TestCase

import _stub


def _load_diagnostics():
    _stub.install_homeassistant()
    return _stub.load(
        "ztediagstub",
        "support_shape",
        "support_bundle",
        "diagnostics",
        const={"DOMAIN": "zte_tracker"},
    )


class _FakeClient:
    model = "F6600P"
    verify_ssl = False
    paths = {
        "wlan_script": "wlan_client_stat_lua.lua",
        "lan_script": "accessdev_landevs_lua.lua",
        "default_scheme": "https",
    }


class _FakeCoordinator:
    update_interval = None
    last_update_success = True
    _available = True
    _paused = False
    _reuse_session = True
    _mesh_topology = False
    _device_cache = {"aa:bb:cc:dd:ee:ff": {}}
    _topo_failures = 0

    def __init__(self):
        self.client = _FakeClient()
        self.data = {
            "devices": {
                "aa:bb:cc:dd:ee:ff": {
                    "name": "Dimitris-Laptop",
                    "ip": "192.168.1.44",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "active": True,
                    "network_type": "WLAN",
                    "mesh_node": "",
                },
                "11:22:33:44:55:66": {
                    "name": "Unknown",
                    "ip": "192.168.1.45",
                    "mac": "11:22:33:44:55:66",
                    "active": False,
                    "network_type": "LAN",
                    "mesh_node": "",
                },
            },
            "router_info": {
                "host": "192.168.1.1",
                "model": "F6600P",
                "status": "connected",
                "ModelName": "F6640",
                "HardwareVer": "V10.0.04",
                "SoftwareVer": "ZTEGF6640P2N10D_V",
                "CpuUsage1": 7,
                "MemUsage": 62,
                "WAN_IPAddress": "94.131.34.223",
                "WAN_Status": "Connected",
                "Uptime": "up 3 days",
                # Real ZTE field names that a denylist does not predict.
                "PPPoEUser": "2101234@example.net",
                "LOID": "GRC1234567890",
                "WlanName": "MyHouse-Guest",
                "WanGw6": "2a02:587:8d1e::1",
            },
        }


class _FakeEntry:
    entry_id = "abc123"
    data = {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "fixture-not-a-real-password",
        "model": "F6600P",
    }
    options = {"session_reuse": True, "mesh_topology": False}


class _FakeHass:
    def __init__(self, coordinator, config_dir=None):
        self.data = {"zte_tracker": {"abc123": coordinator}}
        root = config_dir or tempfile.mkdtemp()
        self.config = types.SimpleNamespace(
            path=lambda *parts: os.path.join(root, *parts)
        )


class TestDiagnostics(TestCase):
    def setUp(self) -> None:
        self.module = _load_diagnostics()
        self.coordinator = _FakeCoordinator()
        self.result = asyncio.run(
            self.module.async_get_config_entry_diagnostics(
                _FakeHass(self.coordinator), _FakeEntry()
            )
        )
        self.blob = json.dumps(self.result)

    def test_credentials_are_redacted(self):
        self.assertNotIn("fixture-not-a-real-password", self.blob)
        self.assertNotIn("admin", self.blob)

    def test_no_device_identity_leaks(self):
        for secret in (
            "Dimitris-Laptop",
            "aa:bb:cc:dd:ee:ff",
            "11:22:33:44:55:66",
            "192.168.1.44",
            "192.168.1.1",
            "94.131.34.223",
        ):
            self.assertNotIn(secret, self.blob, f"{secret} leaked into diagnostics")

    def test_reports_what_the_router_says_it_is(self):
        router = self.result["router"]
        self.assertEqual(router["model_configured"], "F6600P")
        self.assertEqual(router["model_reported"], "F6640")
        self.assertEqual(router["hardware_version"], "V10.0.04")
        self.assertEqual(router["firmware_version"], "ZTEGF6640P2N10D_V")

    def test_reports_the_endpoint_profile(self):
        """The profile is the field that makes an unknown-model report usable."""
        self.assertEqual(
            self.result["router"]["profile"]["wlan_script"],
            "wlan_client_stat_lua.lua",
        )

    def test_device_summary_counts_without_identity(self):
        devices = self.result["devices"]
        self.assertEqual(devices["total"], 2)
        self.assertEqual(devices["active"], 1)
        self.assertEqual(devices["with_hostname"], 1)
        self.assertEqual(devices["by_network_type"], {"WLAN": 1, "LAN": 1})
        self.assertIn("mac", devices["record_keys"])

    def test_non_identity_router_attributes_survive(self):
        attributes = self.result["router_attributes"]
        self.assertEqual(attributes["CpuUsage1"], 7)
        self.assertEqual(attributes["MemUsage"], 62)
        self.assertEqual(attributes["WAN_Status"], "Connected")
        self.assertEqual(attributes["WAN_IPAddress"], "**REDACTED**")

    def test_unknown_firmware_fields_are_dropped_not_pattern_scrubbed(self):
        """An allowlist is the only form that survives a firmware nobody here
        has seen, which is the exact situation diagnostics is collected for."""
        attributes = self.result["router_attributes"]
        for key in ("PPPoEUser", "LOID", "WlanName", "WanGw6"):
            self.assertEqual(attributes[key], "**REDACTED**", key)

    def test_infix_key_names_do_not_defeat_the_allowlist(self):
        """Wrapping each token in \\w* made "mode" match Model and Modem, so
        ModemSerialNumber and ProfileName were admitted verbatim."""
        for key, value in (
            ("ModemSerialNumber", "ZTEGC1234567"),
            ("ProfileName", "otenet_2101234567"),
            ("StatusHostName", "Dimitris-ONT"),
            ("EnableSSIDName", "MyHouse-5G"),
            ("RateLimitUser", "subscriber@isp.gr"),
            ("ByteServerName", "acs.isp.gr"),
        ):
            self.assertEqual(self.module._scrub_value(key, value), "**REDACTED**", key)

    def test_wan_failure_reason_is_not_kept(self):
        """It reads like a useful status, but it is free prose written by the
        firmware, and a WAN failure reason has been observed carrying a
        subscriber number mid sentence. There is no shape to check it against,
        so it does not travel."""
        self.assertEqual(
            self.module._scrub_value("WAN_error_message", "PPP auth failed"),
            "**REDACTED**",
        )
        self.assertEqual(
            self.module._scrub_value(
                "WAN_error_message", "Subscriber 2101234567 rejected"
            ),
            "**REDACTED**",
        )

    def test_plain_wan_status_is_kept(self):
        """A status with a known shape is exactly what a report needs."""
        self.assertEqual(
            self.module._scrub_value("WAN_Status", "Connected"), "Connected"
        )

    def test_host_is_not_re_emitted_through_router_info(self):
        """entry.data redacts the host, then coordinator.data carries a second
        copy. A DDNS name or an IPv6 literal defeats any value-shape scrub."""
        coordinator = _FakeCoordinator()
        coordinator.data["router_info"]["host"] = "router.example.duckdns.org"
        result = asyncio.run(
            self.module.async_get_config_entry_diagnostics(
                _FakeHass(coordinator), _FakeEntry()
            )
        )
        self.assertNotIn("duckdns", json.dumps(result))

    def test_missing_coordinator_is_reported_not_raised(self):
        result = asyncio.run(
            self.module.async_get_config_entry_diagnostics(
                _FakeHass(None).__class__(None), _FakeEntry()
            )
        )
        self.assertIn("error", result)
