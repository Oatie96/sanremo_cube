"""Shared base entity for Sanremo Cube."""
from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CubeDataUpdateCoordinator


class CubeEntity(CoordinatorEntity[CubeDataUpdateCoordinator]):
    """Base entity tying every platform entity to one machine device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CubeDataUpdateCoordinator, unique_key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{unique_key}"
        host = coordinator.entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Sanremo (Net Software Srl — Cube controller)",
            model="Cube",
            configuration_url=f"http://{host}/cube.html",
        )
