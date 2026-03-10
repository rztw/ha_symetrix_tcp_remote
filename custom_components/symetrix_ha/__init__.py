from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType

DOMAIN = "symetrix_ha"

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)

ControlCallback = Callable[[int, int], Awaitable[None] | None]
ConnectionCallback = Callable[[bool], Awaitable[None] | None]
MessageCallback = Callable[[str], Awaitable[None] | None]

PUSH_RE = re.compile(r"#(\d+)=(\d+)")
GS_RE = re.compile(r"\{GS\s+(\d+)\}\s+(\d+)")


@dataclass
class SymetrixClient:
    """Persistent TCP client with basic push parsing."""

    hass: HomeAssistant
    host: str
    port: int
    _writer: Optional[asyncio.StreamWriter] = None
    _task: Optional[asyncio.Task] = None
    _connected: bool = False
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _control_listeners: Dict[int, list[ControlCallback]] = field(default_factory=dict)
    _connection_listeners: list[ConnectionCallback] = field(default_factory=list)
    _message_listeners: list[MessageCallback] = field(default_factory=list)

    async def start(self) -> None:
        """Start background reader / reconnect loop."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = self.hass.loop.create_task(self._run())

    async def stop(self) -> None:
        """Stop client and close connection."""
        self._stop_event.set()
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:  # pragma: no cover - best effort
                pass
        if self._task is not None:
            await self._task

    async def reconnect(self) -> None:
        """Force reconnect to Symetrix."""
        await self.stop()
        # 建立新的 stop_event 以便重新進入 _run 迴圈
        self._stop_event = asyncio.Event()
        await self.start()

    @property
    def connected(self) -> bool:
        return self._connected

    def add_connection_listener(self, cb: ConnectionCallback) -> None:
        self._connection_listeners.append(cb)

    async def _notify_connection(self, connected: bool) -> None:
        self._connected = connected
        for cb in list(self._connection_listeners):
            try:
                res = cb(connected)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as err:  # pragma: no cover
                _LOGGER.error("Connection listener error: %s", err)

    def add_message_listener(self, cb: MessageCallback) -> None:
        self._message_listeners.append(cb)

    async def _notify_message(self, message: str) -> None:
        for cb in list(self._message_listeners):
            try:
                res = cb(message)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as err:  # pragma: no cover
                _LOGGER.error("Message listener error: %s", err)

    async def send_command(self, payload: str) -> None:
        """Send a single command (auto append CRLF)."""
        data = (payload + "\r\n").encode("utf-8")
        if not self._writer or self._writer.is_closing():
            _LOGGER.warning("Not connected, cannot send: %s", payload)
            return
        _LOGGER.debug("Sending to Symetrix %s:%s -> %s", self.host, self.port, payload)
        try:
            self._writer.write(data)
            await self._writer.drain()
        except Exception as err:  # pragma: no cover - network issue
            _LOGGER.error("Error sending data to Symetrix: %s", err)

    async def send_raw(self, command: str) -> None:
        await self.send_command(command)

    async def load_preset(self, preset: int) -> None:
        await self.send_command(f"LP {preset}")

    async def load_global_preset(self, preset: int) -> None:
        await self.send_command(f"LPG {preset}")

    async def flash(self, amount: int) -> None:
        await self.send_command(f"FU {amount}")

    async def reboot(self) -> None:
        await self.send_command("R!")

    async def set_value(self, control: int, value: int) -> None:
        await self.send_command(f"CS {control} {value}")

    async def change_value(self, control: int, inc: bool, step: int) -> None:
        direction = "1" if inc else "0"
        await self.send_command(f"CC {control} {direction} {step}")

    async def get_latest_preset(self) -> None:
        await self.send_command("GPR")

    def add_control_listener(self, control: int, cb: ControlCallback) -> None:
        self._control_listeners.setdefault(control, []).append(cb)

    async def _run(self) -> None:
        """Reconnect loop and reader."""
        backoff = 5
        while not self._stop_event.is_set():
            try:
                _LOGGER.info("Connecting to Symetrix %s:%s", self.host, self.port)
                reader, writer = await asyncio.open_connection(self.host, self.port)
                self._writer = writer
                await self._notify_connection(True)
                _LOGGER.info("Connected to Symetrix %s:%s", self.host, self.port)

                # 啟動時主動詢問一次最新 preset 與 push 控制器
                await self.get_latest_preset()
                await self.send_command("GPU")

                while not self._stop_event.is_set():
                    # Symetrix 以 \r 結尾，所以使用 readuntil(b"\r")
                    chunk = await reader.readuntil(b"\r")
                    if not chunk:
                        raise ConnectionError("EOF from Symetrix")
                    message = chunk.decode("utf-8", errors="ignore").strip("\r\n")
                    if not message or message == "ACK":
                        continue
                    _LOGGER.debug("Received from Symetrix: %s", message)
                    await self._notify_message(message)
                    await self._handle_message(message)

            except Exception as err:  # pragma: no cover - network / parse issues
                if not self._stop_event.is_set():
                    _LOGGER.warning(
                        "Symetrix connection error: %s, retry in %ss", err, backoff
                    )
                    await self._notify_connection(False)
                    await asyncio.sleep(backoff)
            finally:
                await self._notify_connection(False)
                if self._writer is not None:
                    self._writer.close()
                    try:
                        await self._writer.wait_closed()
                    except Exception:
                        pass
                    self._writer = None

        _LOGGER.info("Symetrix client stopped")

    async def _handle_message(self, message: str) -> None:
        """Parse incoming push updates (can contain multiple updates)."""
        # Example push: "#00101=56173" or "#00101=56173#00102=12345"
        if "#" in message:
            parts = message.split("#")
            for part in parts:
                if not part:
                    continue
                if "=" not in part:
                    continue
                left, right = part.split("=", 1)
                left = left.strip()
                right = right.strip()
                if left.isdigit() and right.isdigit():
                    control = int(left)
                    value = int(right)
                    await self._notify_control(control, value)

        # Example GS: "{GS 101} 32768" (可能出現在較大的封包裡，多組並存)
        if "{GS" in message:
            for segment in message.split("{GS"):
                if "}" not in segment:
                    continue
                header, val = segment.split("}", 1)
                header = header.strip()
                val = val.strip()
                # header 例: " 101"
                try:
                    control_str = header.strip()
                    if not control_str:
                        continue
                    control = int(control_str)
                    if not val.split():
                        continue
                    value = int(val.split()[0])
                    await self._notify_control(control, value)
                except Exception:
                    _LOGGER.debug("Failed to parse GS segment: %s", segment)

    async def _notify_control(self, control: int, value: int) -> None:
        listeners = self._control_listeners.get(control)
        if not listeners:
            return
        for cb in list(listeners):
            try:
                res = cb(control, value)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as err:  # pragma: no cover
                _LOGGER.error("Control listener error for %s: %s", control, err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML-based setup is no longer used; keep for backwards compat."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry (UI flow)."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 48631)

    client = SymetrixClient(hass=hass, host=host, port=int(port))

    # 從 symetrix_controls.yaml 讀取控制清單
    def _load_controls() -> list[dict]:
        try:
            controls_path = Path(__file__).parent / "symetrix_controls.yaml"
            if not controls_path.exists():
                return []
            import yaml

            data = yaml.safe_load(controls_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            result: list[dict] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                if "control" not in item or "type" not in item:
                    continue
                result.append(item)
            return result
        except Exception as err:
            _LOGGER.error("Failed to load symetrix_controls.yaml: %s", err)
            return []

    controls = _load_controls()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "controls": controls,
    }

    await client.start()

    # 服務：沿用舊版名稱，但綁定在此 entry 的 client
    async def handle_send_raw(call: ServiceCall) -> None:
        cmd = call.data.get("command")
        if not cmd:
            _LOGGER.error("symetrix_ha.send_raw: 'command' is required")
            return
        await client.send_raw(cmd)

    async def handle_load_preset(call: ServiceCall) -> None:
        preset = int(call.data.get("preset", 1))
        await client.load_preset(preset)

    async def handle_load_global_preset(call: ServiceCall) -> None:
        preset = int(call.data.get("preset", 1))
        await client.load_global_preset(preset)

    async def handle_flash(call: ServiceCall) -> None:
        amount = int(call.data.get("amount", 4))
        await client.flash(amount)

    async def handle_reboot(call: ServiceCall) -> None:
        await client.reboot()

    async def handle_set_value(call: ServiceCall) -> None:
        control = int(call.data.get("control"))
        value = int(call.data.get("value"))
        await client.set_value(control, value)

    async def handle_change_value(call: ServiceCall) -> None:
        control = int(call.data.get("control"))
        step = int(call.data.get("step", 1))
        inc = bool(call.data.get("increase", True))
        await client.change_value(control, inc, step)

    async def handle_get_latest_preset(call: ServiceCall) -> None:
        await client.get_latest_preset()

    # 只在第一次 entry 設定時註冊服務，避免多 entry 重複註冊
    if not hass.services.has_service(DOMAIN, "send_raw"):
        hass.services.async_register(DOMAIN, "send_raw", handle_send_raw)
        hass.services.async_register(DOMAIN, "load_preset", handle_load_preset)
        hass.services.async_register(
            DOMAIN, "load_global_preset", handle_load_global_preset
        )
        hass.services.async_register(DOMAIN, "flash", handle_flash)
        hass.services.async_register(DOMAIN, "reboot", handle_reboot)
        hass.services.async_register(DOMAIN, "set_value", handle_set_value)
        hass.services.async_register(DOMAIN, "change_value", handle_change_value)
        hass.services.async_register(
            DOMAIN, "get_latest_preset", handle_get_latest_preset
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("symetrix_ha entry set up for %s:%s", host, port)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    client: SymetrixClient | None = data.get("client") if data else None
    if client:
        await client.stop()

    return unload_ok

