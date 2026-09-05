"""Data update coordinator for the Sanremo Cube integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CubeApiError, CubeAuthError, CubeClient
from .const import (
    DEFAULT_SCAN_INTERVAL,
    REG_BOILER_TEMPERATURE,
    REG_DAY_COFFEE,
    REG_ECO_BOILER_SETPOINT_X10,
    REG_ECO_TIMER_SECONDS,
    REG_EROGATION_COFFEE_TIME_X10,
    REG_MACHINE_ALARM_STATUS_1,
    REG_MACHINE_STATUS_1,
    REG_MONTH_COFFEE_HIGH,
    REG_MONTH_COFFEE_LOW,
    REG_REMAIN_DAYS_TO_FILTER,
    REG_SCHEDULER_DAY_ENABLED_MASK,
    REG_SCHEDULER_TABLE_START,
    REG_SETPOINT_BOILER_TEMPERATURE_X10,
    REG_SETUP_FLAGS,
    REG_TOT_COFFEE_HIGH,
    REG_TOT_COFFEE_LOW,
    REG_TOT_ML_EROGATED_HIGH,
    REG_TOT_ML_EROGATED_LOW,
    REG_TOT_ML_HIGH,
    REG_TOT_ML_LOADED_BOILER_HIGH,
    REG_TOT_ML_LOADED_BOILER_LOW,
    REG_TOT_ML_LOW,
    REG_WEEK_COFFEE,
    SCHEDULER_SLOT_COUNT,
    SETUP_BIT_ECO_ENABLED,
    SETUP_BIT_SCHEDULER_ENABLED,
    SETUP_BIT_STEAM_BOOSTER_ENABLED,
    STATUS_BIT_ENERGY_SAVING,
    STATUS_BIT_READY,
    STATUS_BIT_STEAM_BOOSTER_HEATING,
    STATUS_BIT_TANK_LEVEL_OK,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SchedulerSlot:
    """One physical scheduler slot in the Cube's daily three-slot table."""

    index: int
    enabled: bool
    on_hour: int
    on_minute: int
    off_hour: int
    off_minute: int


@dataclass
class CubeState:
    """Flattened, typed view of the machine's current state."""

    boiler_temperature: float | None = None
    boiler_setpoint: float | None = None
    eco_boiler_setpoint: float | None = None
    eco_timer_seconds: int | None = None
    shot_time_seconds: float | None = None
    filter_days_remaining: int | None = None

    tank_ok: bool | None = None
    ready: bool | None = None
    steam_booster_heating: bool | None = None

    eco_mode_enabled: bool | None = None
    steam_booster_enabled: bool | None = None
    scheduler_enabled: bool | None = None
    power_on: bool | None = None

    alarm_bits: int = 0

    coffees_today: int | None = None
    coffees_week: int | None = None
    coffees_month: int | None = None
    coffees_total: int | None = None
    ml_erogated_total: int | None = None
    ml_loaded_boiler_total: int | None = None
    ml_total: int | None = None

    scheduler_day_enabled: dict[str, bool] = field(default_factory=dict)
    scheduler_slots: dict[str, list[SchedulerSlot | None]] = field(default_factory=dict)


def _bit(value: int, position: int) -> bool:
    return bool((value >> position) & 1)


def _u32(low: int | None, high: int | None) -> int | None:
    if low is None or high is None:
        return None
    return (int(high) << 16) | int(low)


def parse_state(raw: dict) -> CubeState:
    """Turn the raw merged register map into a CubeState."""
    readonly_regs: dict[int, int] = raw.get("readonly_registers", raw.get("registers", {}))
    readwrite_regs: dict[int, int] = raw.get("readwrite_registers", {})
    state = CubeState()

    if REG_BOILER_TEMPERATURE in readonly_regs:
        state.boiler_temperature = float(readonly_regs[REG_BOILER_TEMPERATURE])
    if REG_SETPOINT_BOILER_TEMPERATURE_X10 in readwrite_regs:
        state.boiler_setpoint = readwrite_regs[REG_SETPOINT_BOILER_TEMPERATURE_X10] / 10
    if REG_ECO_BOILER_SETPOINT_X10 in readwrite_regs:
        state.eco_boiler_setpoint = readwrite_regs[REG_ECO_BOILER_SETPOINT_X10] / 10
    if REG_ECO_TIMER_SECONDS in readwrite_regs:
        state.eco_timer_seconds = readwrite_regs[REG_ECO_TIMER_SECONDS]
    if REG_EROGATION_COFFEE_TIME_X10 in readonly_regs:
        state.shot_time_seconds = readonly_regs[REG_EROGATION_COFFEE_TIME_X10] / 10
    if REG_REMAIN_DAYS_TO_FILTER in readonly_regs:
        state.filter_days_remaining = readonly_regs[REG_REMAIN_DAYS_TO_FILTER]

    status1 = readonly_regs.get(REG_MACHINE_STATUS_1)
    if status1 is not None:
        state.tank_ok = _bit(status1, STATUS_BIT_TANK_LEVEL_OK)
        state.ready = _bit(status1, STATUS_BIT_READY)
        state.steam_booster_heating = _bit(status1, STATUS_BIT_STEAM_BOOSTER_HEATING)
        # User-verified on the physical machine: this flag is set in standby.
        # Ready is deliberately independent while the boiler warms up.
        state.power_on = not _bit(status1, STATUS_BIT_ENERGY_SAVING)

    if REG_MACHINE_ALARM_STATUS_1 in readonly_regs:
        state.alarm_bits = int(readonly_regs[REG_MACHINE_ALARM_STATUS_1])

    setup_flags = readwrite_regs.get(REG_SETUP_FLAGS)
    if setup_flags is not None:
        state.eco_mode_enabled = _bit(setup_flags, SETUP_BIT_ECO_ENABLED)
        state.steam_booster_enabled = _bit(setup_flags, SETUP_BIT_STEAM_BOOSTER_ENABLED)
        state.scheduler_enabled = _bit(setup_flags, SETUP_BIT_SCHEDULER_ENABLED)

    state.coffees_today = readonly_regs.get(REG_DAY_COFFEE)
    state.coffees_week = readonly_regs.get(REG_WEEK_COFFEE)
    state.coffees_month = _u32(
        readonly_regs.get(REG_MONTH_COFFEE_LOW), readonly_regs.get(REG_MONTH_COFFEE_HIGH)
    )
    state.coffees_total = _u32(
        readonly_regs.get(REG_TOT_COFFEE_LOW), readonly_regs.get(REG_TOT_COFFEE_HIGH)
    )
    state.ml_erogated_total = _u32(
        readonly_regs.get(REG_TOT_ML_EROGATED_LOW), readonly_regs.get(REG_TOT_ML_EROGATED_HIGH)
    )
    state.ml_loaded_boiler_total = _u32(
        readonly_regs.get(REG_TOT_ML_LOADED_BOILER_LOW), readonly_regs.get(REG_TOT_ML_LOADED_BOILER_HIGH)
    )
    state.ml_total = _u32(readonly_regs.get(REG_TOT_ML_LOW), readonly_regs.get(REG_TOT_ML_HIGH))

    day_mask = readwrite_regs.get(REG_SCHEDULER_DAY_ENABLED_MASK)
    if day_mask is not None:
        for i, name in enumerate(WEEKDAYS):
            state.scheduler_day_enabled[name] = _bit(day_mask, i)

    # Keep all three physical positions per day. Calendar edits need stable
    # hardware-slot indexes so deleting one window cannot shift another.
    u = REG_SCHEDULER_TABLE_START
    per_day: dict[str, list[SchedulerSlot | None]] = {
        name: [None] * 3 for name in WEEKDAYS
    }
    for i in range(SCHEDULER_SLOT_COUNT):
        day_tag = readwrite_regs.get(u)
        time_reg = readwrite_regs.get(u + 1)
        u += 2
        day_index, slot_index = divmod(i, 3)
        # The panel's own UI order for these 21 slots is Monday-first.
        weekday_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][day_index]
        if day_tag is None or time_reg is None or day_tag == 7:
            continue  # 7 is the "no slot" sentinel used by the panel
        time_on = (time_reg >> 8) & 255
        time_off = time_reg & 255
        per_day[weekday_name][slot_index] = SchedulerSlot(
            index=slot_index,
            enabled=True,
            on_hour=time_on // 4,
            on_minute=(time_on % 4) * 15,
            off_hour=time_off // 4,
            off_minute=(time_off % 4) * 15,
        )
    state.scheduler_slots = per_day

    return state


class CubeDataUpdateCoordinator(DataUpdateCoordinator[CubeState]):
    """Polls the machine on a fixed interval, like the panel itself does."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: CubeClient) -> None:
        self.client = client
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name="Sanremo Cube",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> CubeState:
        try:
            raw = await self.client.async_get_state()
        except CubeAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except CubeApiError as err:
            raise UpdateFailed(str(err)) from err
        return parse_state(raw)
