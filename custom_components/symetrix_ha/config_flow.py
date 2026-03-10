from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from . import DOMAIN


class SymetrixConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
  """Handle a config flow for Symetrix DSP."""

  VERSION = 1

  async def async_step_user(self, user_input=None):
    errors = {}

    if user_input is not None:
      host = user_input[CONF_HOST]
      port = user_input.get(CONF_PORT, 48631)

      await self.async_set_unique_id(f"{host}:{port}")
      self._abort_if_unique_id_configured()

      return self.async_create_entry(
        title=f"Symetrix DSP ({host})",
        data={CONF_HOST: host, CONF_PORT: port},
      )

    data_schema = vol.Schema(
      {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=48631): int,
      }
    )

    return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

