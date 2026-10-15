"""The LLM Toolbox integration.

Adds tools to Home Assistant's Assist LLM API (see ``llm.py``), so every
conversation agent that uses the Assist API can call them. The config entry only
holds the options that pick which tools are offered; there is nothing to set up.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LLM Toolbox from a config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
