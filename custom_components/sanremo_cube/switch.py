"""Switch entities for the Sanremo Cube."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WEEKDAYS
from .coordinator import CubeDataUpdateCoordinator, CubeState
from .entity import CubeEntity


@dataclass(frozen=True, kw_only=True)
class CubeSwitchDescription(SwitchEntityDescription):
    is_on_fn: Callable[[CubeState], bool | None]
    turn_on_fn: Callable[[CubeDataUpdateCoordinator], Awaitable[None]]
    turn_off_fn: Callable[[CubeDataUpdateCoordinator], Awaitable[None]]


SWITCHES: tuple[CubeSwitchDescription, ...] = (
    CubeSwitchDescription(
        key="power",
        translation_key="power",
        is_on_fn=lambda s: s.power_on,
        turn_on_fn=lambda c: c.client.async_power_on(),
        turn_off_fn=lambda c: c.client.async_standby(),
    ),
    CubeSwitchDescription(
        key="eco_mode",
        translation_key="eco_mode",
        entity_category=None,
        is_on_fn=lambda s: s.eco_mode_enabled,
        turn_on_fn=lambda c: c.client.async_set_eco_mode(True),
        turn_off_fn=lambda c: c.client.async_set_eco_mode(False),
    ),
    CubeSwitchDescription(
        key="steam_booster",
        translation_key="steam_booster",
        is_on_fn=lambda s: s.steam_booster_enabled,
        turn_on_fn=lambda c: c.client.async_set_steam_booster(True),
        turn_off_fn=lambda c: c.client.async_set_steam_booster(False),
    ),
    CubeSwitchDescription(
        key="scheduler",
        translation_key="scheduler",
        is_on_fn=lambda s: s.scheduler_enabled,
        turn_on_fn=lambda c: c.client.async_set_scheduler_enabled(True),
        turn_off_fn=lambda c: c.client.async_set_scheduler_enabled(False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CubeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        CubeSwitch(coordinator, description) for description in SWITCHES
    ]
    entities.extend(
        CubeSchedulerDaySwitch(coordinator, day_index, day_name)
        for day_index, day_name in enumerate(WEEKDAYS)
    )
    async_add_entities(entities)


class CubeSwitch(CubeEntity, SwitchEntity):
    entity_description: CubeSwitchDescription

    def __init__(
        self, coordinator: CubeDataUpdateCoordinator, description: CubeSwitchDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs) -> None:
        await self.entity_description.turn_on_fn(self.coordinator)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.entity_description.turn_off_fn(self.coordinator)
        await self.coordinator.async_request_refresh()


class CubeSchedulerDaySwitch(CubeEntity, SwitchEntity):
    """Enable/disable the weekly scheduler for one weekday."""

    _attr_translation_key = "scheduler_day"

    def __init__(
        self, coordinator: CubeDataUpdateCoordinator, day_index: int, day_name: str
    ) -> None:
        super().__init__(coordinator, f"scheduler_{day_name}")
        self._day_index = day_index
        self._day_name = day_name
        self._attr_translation_placeholders = {"day": day_name.capitalize()}

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.scheduler_day_enabled.get(self._day_name)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.async_set_scheduler_day_enabled(self._day_index, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_set_scheduler_day_enabled(self._day_index, False)
        await self.coordinator.async_request_refresh()
