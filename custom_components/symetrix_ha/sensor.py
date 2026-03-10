from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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

    entity = SymetrixLastMessageSensor(client, entry)
    async_add_entities([entity])


class SymetrixLastMessageSensor(SensorEntity):
    """顯示最後一筆從 Symetrix 收到的原始 TCP 資料。"""

    _attr_has_entity_name = True
    # 避免預設就啟用造成大量狀態更新，預設在 Entity Registry 裡是 disabled
    _attr_entity_registry_enabled_default = False

    def __init__(self, client: SymetrixClient, entry: ConfigEntry) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_last_message"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Symetrix DSP",
        }
        self._attr_native_value: str | None = None

    @property
    def name(self) -> str | None:
        return "Last TCP message"

    async def async_added_to_hass(self) -> None:
        @callback
        def _msg_listener(message: str) -> None:
            self._attr_native_value = message
            self.async_write_ha_state()

        self._client.add_message_listener(_msg_listener)

