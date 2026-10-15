"""Fixtures for the LLM Toolbox tests."""

from __future__ import annotations

import socket
import sys

import pytest

if sys.platform == "win32":
    # The HA test plugin blocks socket creation, but Windows event loops need an
    # internal loopback socket pair. Let socketpair() use the real socket class.
    import pytest_socket

    _orig_socketpair = socket.socketpair

    def _socketpair(*args, **kwargs):  # type: ignore[no-untyped-def]
        guarded = socket.socket
        socket.socket = pytest_socket._true_socket  # noqa: SLF001
        try:
            return _orig_socketpair(*args, **kwargs)
        finally:
            socket.socket = guarded

    socket.socketpair = _socketpair

from custom_components.llm_toolbox.const import ALL_TOOLS, CONF_TOOLS, DOMAIN, TITLE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in every test."""


@pytest.fixture(autouse=True)
async def setup_homeassistant(hass: HomeAssistant) -> None:
    """Set up the core component (exposed entities, intents) before each test."""
    assert await async_setup_component(hass, "homeassistant", {})


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return the config entry with every tool enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN, title=TITLE, data={}, options={CONF_TOOLS: list(ALL_TOOLS)}
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the integration."""
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
