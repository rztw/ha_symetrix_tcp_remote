from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
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
    controls: list[Dict] = data.get("controls", [])

    entities: list[SwitchEntity] = []

    for item in controls:
        if item.get("type") != "switch":
            continue

        control = int(item["control"])
        name = item.get("name", f"Control {control}")
        on_value = int(item.get("on_value", 65535))
        off_value = int(item.get("off_value", 0))

        entities.append(
            SymetrixControlSwitch(
                client=client,
                entry=entry,
                control=control,
                name=name,
                on_value=on_value,
                off_value=off_value,
            )
        )

    if entities:
        async_add_entities(entities)


class SymetrixControlSwitch(SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        client: SymetrixClient,
        entry: ConfigEntry,
        control: int,
        name: str,
        on_value: int,
        off_value: int,
    ) -> None:
        self._client = client
        self._control = control
        self._on_value = on_value
        self._off_value = off_value
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_switch_{control}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Symetrix DSP",
        }
        # 預設先當作關閉，這樣一開始就會呈現為真正的 switch toggle
        # 之後實際狀態會由 push / GS 回傳覆蓋
        self._attr_is_on: bool | None = False

    @property
    def is_on(self) -> bool | None:
        return self._attr_is_on

    async def async_added_to_hass(self) -> None:
        @callback
        def _listener(control: int, value: int) -> None:
            if control != self._control:
                return
            self._attr_is_on = value == self._on_value
            self.async_write_ha_state()

        self._client.add_control_listener(self._control, _listener)
        await self._client.send_command(f"GS {self._control}")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.set_value(self._control, self._on_value)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.set_value(self._control, self._off_value)
        self._attr_is_on = False
        self.async_write_ha_state()

