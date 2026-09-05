"""Regression tests for the confirmed live Sanremo Cube HTTP protocol."""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from typing import cast

import aiohttp

# Import the API module without loading Home Assistant's integration setup module.
_COMPONENT_DIR = Path(__file__).parents[1] / "custom_components" / "sanremo_cube"
_custom_components = types.ModuleType("custom_components")
_custom_components.__path__ = [str(_COMPONENT_DIR.parents[0])]
sys.modules.setdefault("custom_components", _custom_components)
_component_package = types.ModuleType("custom_components.sanremo_cube")
_component_package.__path__ = [str(_COMPONENT_DIR)]
sys.modules.setdefault("custom_components.sanremo_cube", _component_package)

from custom_components.sanremo_cube.api import CubeClient  # noqa: E402


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self, **_kwargs):
        return self._payload


class RecordingSession:
    """Minimal aiohttp-session replacement recording real CubeClient requests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        key = kwargs["data"]["key"]
        responses = {
            "150": {"key": 150, "registers": [[0, 1]]},
            "151": {"key": 151, "registers": [[0, 122], [12, 115]]},
            "152": {"key": 152, "registers": [[0, 1250], [12, 0]]},
        }
        return _Response(responses[key])


def test_state_poll_uses_live_form_endpoint_and_keys() -> None:
    """The panel polls /ajax/post as form data with keys 150, 151 and 152."""
    session = RecordingSession()
    client = CubeClient(cast(aiohttp.ClientSession, session), "cube.local")

    raw = asyncio.run(client.async_get_state())

    assert [url for url, _ in session.calls] == [
        "http://cube.local/ajax/post",
        "http://cube.local/ajax/post",
        "http://cube.local/ajax/post",
    ]
    assert [kwargs["data"] for _, kwargs in session.calls] == [
        {"key": "150"},
        {"key": "151"},
        {"key": "152"},
    ]
    assert raw["readonly_registers"] == {0: 122, 12: 115}
    assert raw["readwrite_registers"] == {0: 1250, 12: 0}
