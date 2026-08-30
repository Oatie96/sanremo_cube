"""Number entities (setpoints) for the Sanremo Cube."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CubeDataUpdateCoordinator, CubeState
from .entity import CubeEntity


@dataclass(frozen=True, kw_only=True)
class CubeNumberDescription(NumberEntityDescription):
    value_fn: Callable[[CubeState], float | int | None]
    set_fn: Callable[[CubeDataUpdateCoordinator, float], Awaitable[None]]


NUMBERS: tuple[CubeNumberDescription, ...] = (
    CubeNumberDescription(
        key="boiler_setpoint",
        translation_key="boiler_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=80,
        native_max_value=125,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.boiler_setpoint,
        set_fn=lambda c, v: c.client.async_set_boiler_temperature(v),
    ),
    CubeNumberDescription(
        key="eco_boiler_setpoint",
        translation_key="eco_boiler_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=60,
        native_max_value=120,
        native_step=0.5,
        mode=NumberMode.BOX,
        value_fn=lambda s: s.eco_boiler_setpoint,
        set_fn=lambda c, v: c.client.async_set_eco_boiler_temperature(v),
    ),
    CubeNumberDescription(
        key="eco_timer",
        translation_key="eco_timer",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=180,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda s: (s.eco_timer_seconds / 60) if s.eco_timer_seconds else None,
        set_fn=lambda c, v: c.client.async_set_eco_timer(int(v * 60)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(CubeNumber(coordinator, description) for description in NUMBERS)


class CubeNumber(CubeEntity, NumberEntity):
    entity_description: CubeNumberDescription

    def __init__(
        self, coordinator: CubeDataUpdateCoordinator, description: CubeNumberDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.set_fn(self.coordinator, value)
        await self.coordinator.async_request_refresh()
