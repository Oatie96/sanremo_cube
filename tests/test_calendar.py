from __future__ import annotations

import asyncio
from datetime import datetime

from homeassistant.util import dt as dt_util

from custom_components.sanremo_cube.calendar import CubeScheduleCalendar
from custom_components.sanremo_cube.coordinator import CubeState, SchedulerSlot


class _Coordinator:
    def __init__(self) -> None:
        self.entry = type("Entry", (), {"entry_id": "entry-1"})()
        self.data = CubeState(
            scheduler_slots={
                "monday": [SchedulerSlot(0, True, 7, 0, 8, 30), None, None],
                "tuesday": [None, None, None], "wednesday": [None, None, None],
                "thursday": [None, None, None], "friday": [None, None, None],
                "saturday": [None, None, None], "sunday": [None, None, None],
            }
        )


def test_calendar_expands_a_cube_slot_as_weekly_event() -> None:
    calendar = CubeScheduleCalendar(_Coordinator())
    start = datetime(2026, 9, 7, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    end = datetime(2026, 9, 8, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)

    events = asyncio.run(calendar.async_get_events(None, start, end))

    assert len(events) == 1
    assert events[0].uid == "entry-1:monday:0"
    assert events[0].start.hour == 7
    assert events[0].end.hour == 8
    assert events[0].end.minute == 30
    assert events[0].summary == "Sanremo Cube standby"
    assert events[0].description == "Standby window: machine off at start, on at end."
    assert events[0].rrule == "FREQ=WEEKLY;BYDAY=MO"
