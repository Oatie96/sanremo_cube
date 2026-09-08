from __future__ import annotations

import asyncio
from datetime import datetime

from homeassistant.util import dt as dt_util

from custom_components.sanremo_cube.calendar import CubeScheduleCalendar
from custom_components.sanremo_cube.coordinator import CubeState, SchedulerSlot


class _Client:
    def __init__(self) -> None:
        self.saved_days: list[tuple[int, tuple | None, tuple | None, tuple | None]] = []

    async def async_save_scheduler_day(self, day, slot1, slot2, slot3) -> None:
        self.saved_days.append((day, slot1, slot2, slot3))


class _Coordinator:
    def __init__(self) -> None:
        self.entry = type(
            "Entry",
            (),
            {"entry_id": "entry-1", "data": {"host": "cube.local"}, "title": "Cube"},
        )()
        self.client = _Client()
        self.data = CubeState(
            scheduler_slots={
                "monday": [SchedulerSlot(0, True, 7, 0, 8, 30), None, None],
                "tuesday": [None, None, None],
                "wednesday": [None, None, None],
                "thursday": [None, None, None],
                "friday": [None, None, None],
                "saturday": [None, None, None],
                "sunday": [None, None, None],
            }
        )

    async def async_request_refresh(self) -> None:
        return None


def _calendar() -> tuple[CubeScheduleCalendar, _Coordinator]:
    coordinator = _Coordinator()
    calendar = CubeScheduleCalendar(coordinator)
    calendar.async_write_ha_state = lambda: None
    return calendar, coordinator


def test_calendar_expands_a_cube_slot_as_weekly_event() -> None:
    calendar, _ = _calendar()
    start = datetime(2026, 9, 7, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    end = datetime(2026, 9, 8, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)

    events = asyncio.run(calendar.async_get_events(None, start, end))

    assert len(events) == 1
    assert events[0].uid == "entry-1:monday:0"
    assert events[0].start.hour == 7
    assert events[0].end.hour == 8
    assert events[0].end.minute == 30
    assert events[0].summary == "Sanremo Cube – ON"
    assert events[0].description == "Machine on at start, off at end."
    assert events[0].rrule == "FREQ=WEEKLY;BYDAY=MO"


def test_calendar_create_accepts_home_assistant_service_datetime_keys() -> None:
    """The calendar.create_event service supplies start_date_time/end_date_time."""
    calendar, coordinator = _calendar()
    start = datetime(2026, 9, 8, 6, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    end = datetime(2026, 9, 8, 8, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)

    asyncio.run(
        calendar.async_create_event(
            summary="Sanremo Cube – ON",
            start_date_time=start,
            end_date_time=end,
        )
    )

    assert coordinator.client.saved_days == [(2, (True, 6, 30, 8, 30), None, None)]


def test_calendar_update_accepts_websocket_dtstart_dtend_event_schema() -> None:
    """The frontend WebSocket command sends dtstart/dtend, not start/end."""
    calendar, coordinator = _calendar()
    start = datetime(2026, 9, 7, 6, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    end = datetime(2026, 9, 7, 8, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)

    asyncio.run(
        calendar.async_update_event(
            "entry-1:monday:0",
            {"summary": "Sanremo Cube – ON", "dtstart": start, "dtend": end},
        )
    )

    assert coordinator.client.saved_days == [
        (1, (True, 6, 30, 8, 30), None, None),
    ]
