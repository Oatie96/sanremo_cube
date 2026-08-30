"""Binary sensor entities for the Sanremo Cube."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALARM_BIT_EEPROM_ERROR,
    ALARM_BIT_EROGATION_TIMEOUT,
    ALARM_BIT_LOAD_BOILER_TIMEOUT,
    ALARM_BIT_NEED_CHANGE_FILTERS,
    ALARM_BIT_NTC_BOILER_BROKEN,
    ALARM_BIT_NTC_BOILER_SHORT_CIRCUIT,
    ALARM_BIT_TEMPERATURE_TIMEOUT,
    ALARM_BIT_WIREWOUND_RESISTOR,
    DOMAIN,
)
from .coordinator import CubeDataUpdateCoordinator, CubeState
from .entity import CubeEntity


@dataclass(frozen=True, kw_only=True)
class CubeBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[CubeState], bool | None]


BINARY_SENSORS: tuple[CubeBinarySensorDescription, ...] = (
    CubeBinarySensorDescription(
        key="tank_ok",
        translation_key="tank_ok",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: (s.tank_ok is False) if s.tank_ok is not None else None,
    ),
    CubeBinarySensorDescription(
        key="ready",
        translation_key="ready",
        value_fn=lambda s: s.ready,
    ),
    CubeBinarySensorDescription(
        key="steam_booster_heating",
        translation_key="steam_booster_heating",
        value_fn=lambda s: s.steam_booster_heating,
    ),
    CubeBinarySensorDescription(
        key="alarm_active",
        translation_key="alarm_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: s.alarm_bits != 0,
    ),
    CubeBinarySensorDescription(
        key="need_change_filters",
        translation_key="need_change_filters",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: bool(s.alarm_bits & (1 << ALARM_BIT_NEED_CHANGE_FILTERS)),
    ),
    CubeBinarySensorDescription(
        key="boiler_fault",
        translation_key="boiler_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: bool(
            s.alarm_bits
            & (
                (1 << ALARM_BIT_NTC_BOILER_BROKEN)
                | (1 << ALARM_BIT_NTC_BOILER_SHORT_CIRCUIT)
                | (1 << ALARM_BIT_TEMPERATURE_TIMEOUT)
                | (1 << ALARM_BIT_LOAD_BOILER_TIMEOUT)
                | (1 << ALARM_BIT_WIREWOUND_RESISTOR)
                | (1 << ALARM_BIT_EROGATION_TIMEOUT)
                | (1 << ALARM_BIT_EEPROM_ERROR)
            )
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CubeBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class CubeBinarySensor(CubeEntity, BinarySensorEntity):
    entity_description: CubeBinarySensorDescription

    def __init__(
        self,
        coordinator: CubeDataUpdateCoordinator,
        description: CubeBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
