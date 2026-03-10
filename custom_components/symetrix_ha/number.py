from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.number import NumberEntity
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

    entities: list[NumberEntity] = []

    for item in controls:
        if item.get("type") != "number":
            continue

        control = int(item["control"])
        name = item.get("name", f"Control {control}")
        scale = item.get("scale", "raw")  # "raw" 或 "db_72_12"

        if scale == "db_72_12":
            entities.append(
                SymetrixDbNumberEntity(
                    client=client,
                    entry=entry,
                    control=control,
                    name=name,
                    min_value=float(item.get("min", -72.0)),
                    max_value=float(item.get("max", 12.0)),
                    step=float(item.get("step", 0.5)),
                )
            )
        else:
            entities.append(
                SymetrixRawNumberEntity(
                    client=client,
                    entry=entry,
                    control=control,
                    name=name,
                    min_value=float(item.get("min", 0)),
                    max_value=float(item.get("max", 65535)),
                    step=float(item.get("step", 1)),
                )
            )

    if entities:
        async_add_entities(entities)


class SymetrixBaseNumber(NumberEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        client: SymetrixClient,
        entry: ConfigEntry,
        control: int,
        name: str,
    ) -> None:
        self._client = client
        self._control = control
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_num_{control}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Symetrix DSP",
        }
        self._native_value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._native_value

    async def async_added_to_hass(self) -> None:
        @callback
        def _listener(control: int, value: int) -> None:
            if control != self._control:
                return
            self._native_value = self._from_raw(value)
            self.async_write_ha_state()

        self._client.add_control_listener(self._control, _listener)
        await self._client.send_command(f"GS {self._control}")

    async def async_set_native_value(self, value: float) -> None:
        self._native_value = value
        raw = int(self._to_raw(value))
        await self._client.set_value(self._control, raw)

    def _from_raw(self, value: int) -> float:
        raise NotImplementedError

    def _to_raw(self, value: float) -> int:
        raise NotImplementedError


class SymetrixDbNumberEntity(SymetrixBaseNumber):
    """dB 對應：-72 ~ +12 -> 0~65535"""

    _attr_icon = "mdi:volume-high"

    def __init__(
        self,
        client: SymetrixClient,
        entry: ConfigEntry,
        control: int,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
    ) -> None:
        super().__init__(client, entry, control, name)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    def _from_raw(self, value: int) -> float:
        db = -72.0 + 84.0 * (value / 65535.0)
        return round(db, 1)

    def _to_raw(self, value: float) -> int:
        raw = ((value + 72.0) / 84.0) * 65535.0
        raw = max(0.0, min(65535.0, raw))
        return int(raw)


class SymetrixRawNumberEntity(SymetrixBaseNumber):
    """直接用 0~65535 的 raw 數值 slider。"""

    def __init__(
        self,
        client: SymetrixClient,
        entry: ConfigEntry,
        control: int,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
    ) -> None:
        super().__init__(client, entry, control, name)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    def _from_raw(self, value: int) -> float:
        return float(value)

    def _to_raw(self, value: float) -> int:
        return int(value)

