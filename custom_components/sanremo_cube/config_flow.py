"""Config flow for the Sanremo Cube integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CubeApiError, CubeClient
from .const import CONF_PIN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PIN): str,
    }
)


class SanremoCubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sanremo Cube."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            pin = user_input.get(CONF_PIN) or None

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = CubeClient(session, host, pin)
            try:
                await client.async_get_state()
            except CubeApiError:
                _LOGGER.exception("Could not reach Sanremo Cube at %s", host)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Sanremo Cube ({host})",
                    data={CONF_HOST: host, CONF_PIN: pin},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
