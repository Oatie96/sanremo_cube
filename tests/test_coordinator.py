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
