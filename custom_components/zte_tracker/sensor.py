"""Sensor platform for ZTE Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as ha_dt

from .const import DOMAIN, ICON
from .coordinator import ZteDataCoordinator

try:
    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

    _DEV_SIGNAL = SensorDeviceClass.SIGNAL_STRENGTH
    _STATE_MEASUREMENT = SensorStateClass.MEASUREMENT
except ImportError:  # pragma: no cover - fallback for lightweight test stubs
    _DEV_SIGNAL = "signal_strength"
    _STATE_MEASUREMENT = "measurement"

_CELLULAR_METRIC_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "cellular_network_type",
        "name": "Cellular Network Type",
        "icon": "mdi:antenna",
        "extra_keys": (
            "cellular_operator",
            "cellular_plmn",
            "cellular_roaming",
            "cellular_ca_status",
            "cellular_signal_bars",
        ),
    },
    {
        "key": "cellular_signal_bars",
        "name": "Cellular Signal Bars",
        "icon": "mdi:signal",
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "lte_band",
        "name": "LTE Band",
        "icon": "mdi:radio-tower",
        "extra_keys": (
            "lte_cell_id",
            "lte_cell_id_hex",
            "lte_pci",
            "lte_earfcn",
            "lte_bandwidth",
            "cellular_ca_status",
            "lte_ca_scell_info",
            "lte_cells",
        ),
    },
    {
        "key": "lte_rsrp_dbm",
        "name": "LTE RSRP",
        "icon": "mdi:signal-4g",
        "unit": "dBm",
        "device_class": _DEV_SIGNAL,
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "lte_rsrq_db",
        "name": "LTE RSRQ",
        "icon": "mdi:signal-4g",
        "unit": "dB",
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "lte_sinr_db",
        "name": "LTE SINR",
        "icon": "mdi:signal-4g",
        "unit": "dB",
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "lte_rssi_dbm",
        "name": "LTE RSSI",
        "icon": "mdi:signal-4g",
        "unit": "dBm",
        "device_class": _DEV_SIGNAL,
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "nr5g_band",
        "name": "5G NR Band",
        "icon": "mdi:signal-5g",
        "extra_keys": (
            "nr5g_cell_id",
            "nr5g_cell_id_hex",
            "nr5g_pci",
            "nr5g_arfcn",
            "nr5g_bandwidth",
            "nr5g_cells",
        ),
    },
    {
        "key": "nr5g_rsrp_dbm",
        "name": "5G NR RSRP",
        "icon": "mdi:signal-5g",
        "unit": "dBm",
        "device_class": _DEV_SIGNAL,
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "nr5g_rsrq_db",
        "name": "5G NR RSRQ",
        "icon": "mdi:signal-5g",
        "unit": "dB",
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "nr5g_sinr_db",
        "name": "5G NR SINR",
        "icon": "mdi:signal-5g",
        "unit": "dB",
        "state_class": _STATE_MEASUREMENT,
    },
    {
        "key": "nr5g_rssi_dbm",
        "name": "5G NR RSSI",
        "icon": "mdi:signal-5g",
        "unit": "dBm",
        "device_class": _DEV_SIGNAL,
        "state_class": _STATE_MEASUREMENT,
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE sensor from config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        ZteRouterSensor(coordinator, entry),
        ZteDeviceCountSensor(coordinator, entry),
    ]
    paths = getattr(getattr(coordinator, "client", None), "paths", None) or {}
    if paths.get("cellular_metrics"):
        for spec in _CELLULAR_METRIC_SPECS:
            entities.append(ZteCellularMetricSensor(coordinator, entry, spec))

    async_add_entities(entities)


class ZteBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for ZTE sensors."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        router_info = (coordinator.data or {}).get("router_info", {}) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer=router_info.get("ManuFacturer", "ZTE"),
            model=router_info.get("ModelName") or coordinator.client.model,
            sw_version=router_info.get("SoftwareVer"),
            hw_version=router_info.get("HardwareVer"),
            # The scheme is per profile and the user can override it, so the
            # link is taken from the client rather than assumed. It was
            # hardcoded to https, which is a dead link on an http only unit.
            configuration_url=getattr(coordinator.client, "base_url", None),
        )


class ZteRouterSensor(ZteBaseSensor):
    """Sensor representing the router status."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the router sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"ZTE Router {coordinator.client.host}"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = ICON

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        return router_info.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        # Return a copy to avoid mutating shared coordinator.data
        interval = self.coordinator.update_interval
        return {
            **router_info,
            "last_update": ha_dt.now().isoformat(),
            "poll_interval": int(interval.total_seconds()) if interval else None,
        }


class ZteDeviceCountSensor(ZteBaseSensor):
    """Sensor for the number of connected devices."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the device count sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"ZTE Router {coordinator.client.host} Connected Devices"
        self._attr_unique_id = f"{entry.entry_id}_device_count"
        self._attr_icon = "mdi:devices"
        self._attr_native_unit_of_measurement = "devices"

    @property
    def native_value(self) -> int:
        """Return the number of connected devices."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        return len([d for d in devices.values() if d.get("active")])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes, including the list of detected devices."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device_list = [
            f"{mac}({device.get('name', 'Unknown')}-{device.get('ip', '')})"
            for mac, device in devices.items()
        ]
        return {
            "devices": device_list,
            "num_devices": len([d for d in devices.values() if d.get("active")]),
        }


class ZteCellularMetricSensor(ZteBaseSensor):
    """Sensor exposing a 5G NR / 4G LTE radio metric from router_info."""

    def __init__(
        self,
        coordinator: ZteDataCoordinator,
        entry: ConfigEntry,
        spec: dict[str, Any],
    ) -> None:
        """Initialize the cellular metric sensor."""
        super().__init__(coordinator, entry)
        self._key: str = spec["key"]
        self._extra_keys: tuple[str, ...] = spec.get("extra_keys", ())
        self._attr_name = f"ZTE Router {coordinator.client.host} {spec['name']}"
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_icon = spec.get("icon", ICON)
        if "unit" in spec:
            self._attr_native_unit_of_measurement = spec["unit"]
        if "device_class" in spec:
            self._attr_device_class = spec["device_class"]
        if "state_class" in spec:
            self._attr_state_class = spec["state_class"]

    @property
    def native_value(self) -> Any:
        """Return the current value of the cellular metric."""
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        return router_info.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed cell attributes when configured for this sensor."""
        if not self._extra_keys:
            return {}
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        return {
            key: router_info[key]
            for key in self._extra_keys
            if key in router_info and router_info[key] is not None
        }
