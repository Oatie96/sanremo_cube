"""The Sanremo Cube integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CubeClient
from .const import CONF_PIN, DOMAIN, WEEKDAYS
from .coordinator import CubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
]

SERVICE_SET_SCHEDULE = "set_schedule"

_SLOT_SCHEMA = vol.Schema(
    {
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Required("start"): cv.time,
        vol.Required("end"): cv.time,
    }
)

SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("day"): vol.In(WEEKDAYS),
        vol.Optional("slot1"): _SLOT_SCHEMA,
        vol.Optional("slot2"): _SLOT_SCHEMA,
        vol.Optional("slot3"): _SLOT_SCHEMA,
        vol.Optional("copy_to", default=[]): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sanremo Cube from a config entry."""
    session = async_get_clientsession(hass)
    client = CubeClient(session, entry.data[CONF_HOST], entry.data.get(CONF_PIN))

    coordinator = CubeDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_set_schedule(call: ServiceCall) -> None:
        target_coordinator: CubeDataUpdateCoordinator = hass.data[DOMAIN][
            call.data["config_entry_id"]
        ]
        day_index = WEEKDAYS.index(call.data["day"])  # 0=Sunday..6=Saturday

        def _slot(key: str):
            raw = call.data.get(key)
            if raw is None:
                return None
            start, end = raw["start"], raw["end"]
            return (raw.get("enabled", True), start.hour, start.minute, end.hour, end.minute)

        await target_coordinator.client.async_save_scheduler_day(
            day=day_index,
            slot1=_slot("slot1"),
            slot2=_slot("slot2"),
            slot3=_slot("slot3"),
            copy_to=call.data.get("copy_to", []),
        )
        await target_coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_SCHEDULE, _handle_set_schedule, schema=SET_SCHEDULE_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_SCHEDULE)
    return unload_ok
