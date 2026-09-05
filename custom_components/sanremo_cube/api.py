"""Thin async client for the Sanremo Cube local HTTP API.

Reverse-engineered from the machine's own web panel (cube.html / cube.js):
every action is a POST to /default.aspx/PostAction with a numeric reqCode
and a JSON-encoded payload. See the project README for the full command
reference this integration is built on.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    DEFAULT_TIMEOUT,
    ENDPOINT,
    ID_BOILER_TEMPERATURE,
    ID_ECO_BOILER_SETPOINT_X10,
    ID_ECO_MODE,
    ID_ECO_TIMER_SECONDS,
    ID_POWER_ON,
    ID_STANDBY_ON,
    ID_STEAM_BOOSTER,
    REQ_GET_READONLY_PARAMETERS,
    REQ_GET_READWRITE_PARAMETERS,
    REQ_GET_SYSTEM_PARAMETERS,
    REQ_LOGIN,
    REQ_REBOOT,
    REQ_SAVE_SCHEDULER_DAY,
    REQ_SET_SCHEDULER_DAY_STATUS,
    REQ_SET_SCHEDULER_STATUS,
    REQ_SET_VALUE,
)

_LOGGER = logging.getLogger(__name__)


class CubeApiError(Exception):
    """Raised on any transport or protocol failure talking to the machine."""


class CubeAuthError(CubeApiError):
    """Raised when the machine reports the session as expired/invalid."""


class CubeClient:
    """Talks to one Sanremo Cube controller over the local network."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        pin: str | None = None,
    ) -> None:
        self._session = session
        self._host = host.rstrip("/")
        self._pin = pin
        self._logged_in = False

    @property
    def base_url(self) -> str:
        return f"http://{self._host}{ENDPOINT}"

    async def _post(self, req_code: str, data: dict[str, Any] | None) -> Any:
        """POST one reqCode/data pair and return the decoded payload."""
        body: dict[str, Any] = {"key": req_code}
        if data:
            body.update(data)
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT):
                async with self._session.post(self.base_url, data=body) as resp:
                    resp.raise_for_status()
                    envelope = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CubeApiError(f"Error talking to {self._host}: {err}") from err

        raw = envelope.get("d") if isinstance(envelope, dict) and "d" in envelope else envelope
        if raw is None:
            return None
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError) as err:
            raise CubeApiError(f"Unexpected response for reqCode {req_code}: {raw!r}") from err

        if isinstance(payload, dict) and payload.get("sessionExpired"):
            self._logged_in = False
            raise CubeAuthError("Session expired")

        return payload

    async def async_ensure_login(self) -> None:
        """Log in with the configured PIN, if one was set and we're not in already.

        Many Cube panels on a trusted LAN have no PIN configured at all, in which
        case this is a no-op — normal reqCode calls simply work without it.
        """
        if self._logged_in or not self._pin:
            return
        await self._post(REQ_LOGIN, {"pin": self._pin})
        self._logged_in = True

    async def async_get_state(self) -> dict[str, Any]:
        """Fetch the three parameter blocks the panel itself polls.

        Register indexes are local to a response block: the read-only (151)
        and read-write (152) blocks both start at register 0. Keep them
        separate so a value from one block can never overwrite another.
        """
        await self.async_ensure_login()
        merged: dict[str, Any] = {}
        register_blocks = {
            REQ_GET_SYSTEM_PARAMETERS: "system_registers",
            REQ_GET_READONLY_PARAMETERS: "readonly_registers",
            REQ_GET_READWRITE_PARAMETERS: "readwrite_registers",
        }
        for req_code in (
            REQ_GET_SYSTEM_PARAMETERS,
            REQ_GET_READONLY_PARAMETERS,
            REQ_GET_READWRITE_PARAMETERS,
        ):
            result = await self._post(req_code, None)
            if not isinstance(result, dict):
                continue
            registers = result.get("registers")
            if registers:
                reg_map: dict[int, int] = {}
                for entry in registers:
                    try:
                        idx, val = entry[0], entry[1]
                    except (IndexError, TypeError):
                        continue
                    reg_map[int(idx)] = val
                merged[register_blocks[req_code]] = reg_map
            for key, val in result.items():
                if key != "registers":
                    merged[key] = val
        return merged

    # --- generic setter (reqCode 200) -------------------------------------

    async def async_set_value(self, value_id: int, value: Any) -> None:
        await self.async_ensure_login()
        await self._post(REQ_SET_VALUE, {"id": value_id, "value": value})

    async def async_power_on(self) -> None:
        # User-verified on the physical machine: Cube command 11 powers on.
        await self.async_set_value(ID_STANDBY_ON, 1)

    async def async_standby(self) -> None:
        # Cube command 12 enters standby (despite its legacy constant name).
        await self.async_set_value(ID_POWER_ON, 1)

    async def async_set_eco_mode(self, on: bool) -> None:
        await self.async_set_value(ID_ECO_MODE, 1 if on else 0)

    async def async_set_steam_booster(self, on: bool) -> None:
        await self.async_set_value(ID_STEAM_BOOSTER, 1 if on else 0)

    async def async_set_boiler_temperature(self, celsius: float) -> None:
        await self.async_set_value(ID_BOILER_TEMPERATURE, celsius)

    async def async_set_eco_boiler_temperature(self, celsius: float) -> None:
        await self.async_set_value(ID_ECO_BOILER_SETPOINT_X10, round(celsius * 10))

    async def async_set_eco_timer(self, seconds: int) -> None:
        await self.async_set_value(ID_ECO_TIMER_SECONDS, seconds)

    async def async_reboot(self) -> None:
        await self.async_ensure_login()
        await self._post(REQ_REBOOT, None)

    # --- scheduler ----------------------------------------------------------

    async def async_set_scheduler_enabled(self, enabled: bool) -> None:
        await self.async_ensure_login()
        await self._post(REQ_SET_SCHEDULER_STATUS, {"enabled": 1 if enabled else 0})

    async def async_set_scheduler_day_enabled(self, day: int, enabled: bool) -> None:
        """day: 0=Sunday .. 6=Saturday (JS Date.getDay() convention)."""
        await self.async_ensure_login()
        await self._post(
            REQ_SET_SCHEDULER_DAY_STATUS, {"day": day, "enabled": 1 if enabled else 0}
        )

    async def async_save_scheduler_day(
        self,
        day: int,
        slot1: tuple[bool, int, int, int, int] | None = None,
        slot2: tuple[bool, int, int, int, int] | None = None,
        slot3: tuple[bool, int, int, int, int] | None = None,
        copy_to: list[str] | None = None,
    ) -> None:
        """Save up to three on/off windows for one day.

        Each slot is (enabled, on_hour, on_minute, off_hour, off_minute).
        copy_to is a list of weekday names ("monday".."sunday") to replicate
        this same save onto, in one call, mirroring the panel's own
        "copy to days" option.
        """
        await self.async_ensure_login()
        copy_to = copy_to or []

        def slot_fields(prefix: str, slot: tuple[bool, int, int, int, int] | None) -> dict:
            if slot is None:
                return {
                    f"en{prefix}": 0,
                    f"on{prefix}H": 0,
                    f"on{prefix}M": 0,
                    f"off{prefix}H": 0,
                    f"off{prefix}M": 0,
                }
            en, on_h, on_m, off_h, off_m = slot
            return {
                f"en{prefix}": 1 if en else 0,
                f"on{prefix}H": on_h,
                f"on{prefix}M": on_m,
                f"off{prefix}H": off_h,
                f"off{prefix}M": off_m,
            }

        payload: dict[str, Any] = {"day": day}
        payload.update(slot_fields("1", slot1))
        payload.update(slot_fields("2", slot2))
        payload.update(slot_fields("3", slot3))
        for weekday in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
            payload[f"copy{weekday.capitalize()}"] = 1 if weekday in [
                w[:3] for w in copy_to
            ] else 0

        await self._post(REQ_SAVE_SCHEDULER_DAY, payload)
