from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SymetrixClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: SymetrixClient = data["client"]

    entities: list[ButtonEntity] = [
        SymetrixFlashButton(client, entry),
        SymetrixRebootButton(client, entry),
        SymetrixReconnectButton(client, entry),
    ]

    async_add_entities(entities)


class SymetrixBaseButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, client: SymetrixClient, entry: ConfigEntry) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_name_key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Symetrix DSP",
        }


class SymetrixFlashButton(SymetrixBaseButton):
    _attr_translation_key = "flash"
    _attr_name_key = "flash"

    @property
    def name(self) -> str | None:
        return "Flash DSP"

    async def async_press(self, **kwargs: Any) -> None:
        await self._client.flash(4)


class SymetrixRebootButton(SymetrixBaseButton):
    _attr_translation_key = "reboot"
    _attr_name_key = "reboot"

    @property
    def name(self) -> str | None:
        return "Reboot DSP"

    async def async_press(self, **kwargs: Any) -> None:
        await self._client.reboot()


class SymetrixReconnectButton(SymetrixBaseButton):
    _attr_translation_key = "reconnect"
    _attr_name_key = "reconnect"

    @property
    def name(self) -> str | None:
        return "Reconnect"

    async def async_press(self, **kwargs: Any) -> None:
        await self._client.reconnect()

