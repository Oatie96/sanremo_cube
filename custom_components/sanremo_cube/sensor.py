"""Sensor entities for the Sanremo Cube."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CubeDataUpdateCoordinator, CubeState
from .entity import CubeEntity


@dataclass(frozen=True, kw_only=True)
class CubeSensorDescription(SensorEntityDescription):
    value_fn: Callable[[CubeState], float | int | None]


SENSORS: tuple[CubeSensorDescription, ...] = (
    CubeSensorDescription(
        key="boiler_temperature",
        translation_key="boiler_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.boiler_temperature,
    ),
    CubeSensorDescription(
        key="boiler_setpoint",
        translation_key="boiler_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.boiler_setpoint,
    ),
    CubeSensorDescription(
        key="shot_time",
        translation_key="shot_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.shot_time_seconds,
    ),
    CubeSensorDescription(
        key="filter_days_remaining",
        translation_key="filter_days_remaining",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda s: s.filter_days_remaining,
    ),
    CubeSensorDescription(
        key="coffees_today",
        translation_key="coffees_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.coffees_today,
    ),
    CubeSensorDescription(
        key="coffees_week",
        translation_key="coffees_week",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.coffees_week,
    ),
    CubeSensorDescription(
        key="coffees_month",
        translation_key="coffees_month",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.coffees_month,
    ),
    CubeSensorDescription(
        key="coffees_total",
        translation_key="coffees_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.coffees_total,
    ),
    CubeSensorDescription(
        key="total_water_erogated",
        translation_key="total_water_erogated",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.ml_erogated_total,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(CubeSensor(coordinator, description) for description in SENSORS)


class CubeSensor(CubeEntity, SensorEntity):
    entity_description: CubeSensorDescription

    def __init__(
        self, coordinator: CubeDataUpdateCoordinator, description: CubeSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
