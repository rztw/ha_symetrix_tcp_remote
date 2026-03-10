from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SymetrixClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: SymetrixClient = data["client"]

    entity = SymetrixConnectionBinarySensor(client, entry)
    async_add_entities([entity])


class SymetrixConnectionBinarySensor(BinarySensorEntity):
    """顯示目前是否連線到 Symetrix 的狀態。"""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, client: SymetrixClient, entry: ConfigEntry) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_connection"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Symetrix DSP",
        }
        self._attr_is_on = client.connected

    @property
    def name(self) -> str | None:
        return "Connection"

    @property
    def is_on(self) -> bool | None:
        return self._attr_is_on

    async def async_added_to_hass(self) -> None:
        @callback
        def _conn_listener(connected: bool) -> None:
            self._attr_is_on = connected
            self.async_write_ha_state()

        self._client.add_connection_listener(_conn_listener)

