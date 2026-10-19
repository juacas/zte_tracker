"""E2633 specifics of the entity platforms: the reboot button and the ``clients`` attribute."""

from __future__ import annotations

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.components.recorder.db_schema import MAX_STATE_ATTRS_BYTES
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker import button, sensor
from custom_components.zte_tracker.const import DOMAIN
from custom_components.zte_tracker.zteclient.zte_client import _MODELS


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, entry_id="entry-1", title="Router", data={})


def _coordinator(model: str, devices: dict):
    coordinator = SimpleNamespace()
    coordinator.client = SimpleNamespace(
        host="192.0.2.1", model=model, paths=_MODELS[model], base_url="https://192.0.2.1"
    )
    coordinator.data = {"devices": devices, "router_info": {"status": "connected"}}
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(seconds=60)
    return coordinator


def _wifi_devices(count: int, name_length: int = 24) -> dict:
    return {
        f"02:00:00:00:{i // 256:02x}:{i % 256:02x}": {
            "name": f"host-{i}".ljust(name_length, "x"),
            "ip": f"192.0.2.{i % 250 + 1}",
            "active": True,
            "network_type": "WLAN",
            "port": "2.4G",
            "rssi": -60,
            "wireless_mode": "802.11ax",
            "rx_rate": 1200000,
            "tx_rate": 800000,
        }
        for i in range(count)
    }


def _count_attributes(model: str, devices: dict) -> dict:
    count_sensor = sensor.ZteDeviceCountSensor(_coordinator(model, devices), _entry())
    return count_sensor.extra_state_attributes


def _recorder_bytes(attributes: dict) -> int:
    """Size the recorder sees: the sensor's attributes plus what Home Assistant adds."""
    full = {
        **attributes,
        "friendly_name": "ZTE Router 192.0.2.1 Connected Devices",
        "icon": "mdi:devices",
        "unit_of_measurement": "devices",
    }
    return len(json.dumps(full, separators=(",", ":"), ensure_ascii=False).encode())


@pytest.mark.parametrize("model", ["F6640", "H288A", "F8748"])
def test_other_models_do_not_get_the_clients_attribute(model) -> None:
    attributes = _count_attributes(model, _wifi_devices(3))
    assert "clients" not in attributes
    assert set(attributes) == {"devices", "num_devices"}


def test_e2633_clients_attribute_lists_active_wifi_clients() -> None:
    devices = _wifi_devices(2)
    devices["02:00:00:00:99:99"] = {
        "name": "left", "ip": "", "active": False, "network_type": "WLAN", "port": "5G",
    }
    devices["02:00:00:00:99:98"] = {
        "name": "wired", "ip": "", "active": True, "network_type": "LAN", "port": "lan1",
    }
    attributes = _count_attributes("E2633", devices)
    assert [c["mac"] for c in attributes["clients"]] == [
        "02:00:00:00:00:00",
        "02:00:00:00:00:01",
    ]
    assert attributes["clients"][0] == {
        "mac": "02:00:00:00:00:00", "ip": "192.0.2.1", "name": "host-0".ljust(24, "x"),
        "band": "2.4G", "rssi": -60, "mode": "802.11ax", "rx_rate": 1200000, "tx_rate": 800000,
    }
    assert "clients_truncated" not in attributes


@pytest.mark.parametrize("count", [10, 80, 150])
def test_e2633_attributes_stay_under_the_recorder_limit(count) -> None:
    attributes = _count_attributes("E2633", _wifi_devices(count))
    assert _recorder_bytes(attributes) <= MAX_STATE_ATTRS_BYTES
    # The count itself must never be cut.
    assert attributes["num_devices"] == count


def test_e2633_clients_are_cut_not_dropped_when_there_are_too_many() -> None:
    attributes = _count_attributes("E2633", _wifi_devices(150))
    assert 0 < len(attributes["clients"]) < 150
    assert attributes["clients_truncated"] is True


def test_e2633_clients_add_nothing_when_the_device_list_alone_fills_the_budget() -> None:
    """The pre-existing ``devices`` attribute alone passes 16 KB at ~400 devices; ``clients``
    must not make that worse."""
    attributes = _count_attributes("E2633", _wifi_devices(400))
    assert attributes["clients"] == []
    assert attributes["clients_truncated"] is True


@pytest.mark.asyncio
async def test_no_reboot_button_for_e2633_but_one_for_other_models(mock_hass) -> None:
    for model, expected in (("E2633", 0), ("F6640", 1)):
        mock_hass.data = {DOMAIN: {"entry-1": _coordinator(model, {})}}
        added: list = []
        await button.async_setup_entry(mock_hass, _entry(), added.extend)
        assert len(added) == expected, model
