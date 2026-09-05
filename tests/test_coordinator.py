"""Regression coverage for distinct Sanremo Cube read-only/writeable register blocks."""
from __future__ import annotations

from custom_components.sanremo_cube.coordinator import parse_state


def test_parse_state_reads_each_value_from_its_confirmed_register_block() -> None:
    """Register 0 has different meanings in API replies 151 and 152."""
    state = parse_state(
        {
            "readonly_registers": {
                0: 122,
                9: 27,
                10: 4,
                12: 115,
                14: 0,
                21: 10,
            },
            "readwrite_registers": {
                0: 1250,
                17: 200,
                60: 2,
                67: 1800,
                68: 950,
            },
        }
    )

    assert state.boiler_temperature == 122.0
    assert state.boiler_setpoint == 125.0
    assert state.shot_time_seconds == 2.7
    assert state.filter_days_remaining == 4
    assert state.ready is True
    assert state.eco_mode_enabled is True
    assert state.steam_booster_enabled is True
    assert state.scheduler_day_enabled["monday"] is True
    assert state.eco_timer_seconds == 1800
    assert state.eco_boiler_setpoint == 95.0


def test_parse_state_preserves_physical_scheduler_slot_positions() -> None:
    """Inactive slots must remain identifiable for safe calendar edits."""
    state = parse_state(
        {
            "readwrite_registers": {
                18: 1,
                19: (7 * 4 << 8) | (8 * 4),
                20: 7,
                21: 0,
                22: 1,
                23: (17 * 4 << 8) | (18 * 4),
            }
        }
    )

    monday = state.scheduler_slots["monday"]
    assert len(monday) == 3
    assert monday[0].index == 0
    assert monday[0].on_hour == 7
    assert monday[0].off_hour == 8
    assert monday[1] is None
    assert monday[2].index == 2
