"""Native calendar view and editor for a Sanremo Cube weekly schedule."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.calendar.const import CalendarEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import CubeDataUpdateCoordinator, SchedulerSlot

_DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_BYDAY = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([CubeScheduleCalendar(hass.data[DOMAIN][entry.entry_id])])


class CubeScheduleCalendar(CalendarEntity):
    """Expose the Cube's seven-day, three-slot schedule as a native calendar."""

    _attr_has_entity_name = True
    _attr_name = "Weekly schedule"
    _attr_translation_key = "weekly_schedule"
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT | CalendarEntityFeature.UPDATE_EVENT | CalendarEntityFeature.DELETE_EVENT
    )

    def __init__(self, coordinator: CubeDataUpdateCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_weekly_schedule"

    def _uid(self, day: str, index: int) -> str:
        return f"{self.coordinator.entry.entry_id}:{day}:{index}"

    def _events_for_date(self, date, tzinfo) -> list[CalendarEvent]:
        day = _DAY_NAMES[date.weekday()]
        events = []
        for slot in self.coordinator.data.scheduler_slots.get(day, []):
            if slot is None:
                continue
            start = datetime.combine(date, time(slot.on_hour, slot.on_minute), tzinfo=tzinfo)
            end = datetime.combine(date, time(slot.off_hour, slot.off_minute), tzinfo=tzinfo)
            events.append(CalendarEvent(start=start, end=end, summary="Sanremo Cube", uid=self._uid(day, slot.index), rrule=f"FREQ=WEEKLY;BYDAY={_BYDAY[date.weekday()]}"))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
        for offset in range(8):
            events = self._events_for_date((now + timedelta(days=offset)).date(), now.tzinfo)
            for candidate in events:
                if candidate.end_datetime_local > now:
                    return candidate
        return None

    async def async_get_events(self, hass: HomeAssistant | None, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        date = start_date.date()
        while date <= end_date.date():
            for candidate in self._events_for_date(date, start_date.tzinfo):
                if candidate.end_datetime_local > start_date and candidate.start_datetime_local < end_date:
                    events.append(candidate)
            date += timedelta(days=1)
        return events

    async def _save_day(self, day: str, slots: list[SchedulerSlot | None]) -> None:
        def as_payload(slot: SchedulerSlot | None):
            if slot is None:
                return None
            return (True, slot.on_hour, slot.on_minute, slot.off_hour, slot.off_minute)
        await self.coordinator.client.async_save_scheduler_day(
            day=(day, "monday", "tuesday", "wednesday", "thursday", "friday", "saturday").index(day),
            slot1=as_payload(slots[0]), slot2=as_payload(slots[1]), slot3=as_payload(slots[2]),
        )
        await self.coordinator.async_request_refresh()

    async def async_create_event(self, **kwargs) -> None:
        start, end = kwargs["start"], kwargs["end"]
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("Cube schedules require start and end times")
        if start.date() != end.date() or end <= start or start.minute % 15 or end.minute % 15:
            raise ValueError("Use same-day 15-minute time windows")
        day = _DAY_NAMES[start.weekday()]
        slots = list(self.coordinator.data.scheduler_slots.get(day, [None] * 3))
        try:
            index = slots.index(None)
        except ValueError as err:
            raise ValueError("A Cube supports at most three windows per day") from err
        slots[index] = SchedulerSlot(index, True, start.hour, start.minute, end.hour, end.minute)
        await self._save_day(day, slots)
        self.async_write_ha_state()

    async def async_delete_event(self, uid: str, recurrence_id=None, recurrence_range=None) -> None:
        entry_id, day, raw_index = uid.split(":")
        if entry_id != self.coordinator.entry.entry_id or day not in _DAY_NAMES:
            raise ValueError("Unknown Cube schedule event")
        slots = list(self.coordinator.data.scheduler_slots.get(day, [None] * 3))
        slots[int(raw_index)] = None
        await self._save_day(day, slots)
        self.async_write_ha_state()

    async def async_update_event(self, uid: str, event: dict, recurrence_id=None, recurrence_range=None) -> None:
        await self.async_delete_event(uid, recurrence_id, recurrence_range)
        await self.async_create_event(**event)
