"""Constants for the LLM Toolbox integration."""

import logging

DOMAIN = "llm_toolbox"
LOGGER = logging.getLogger(__package__)

TITLE = "LLM Toolbox"

CONF_TOOLS = "tools"

# Ids of the tools contributed to the Assist LLM API (llm.py), as stored in the
# options. Every tool is on by default.
TOOL_CLIMATE_MODES = "climate_modes"
TOOL_SELECT_OPTION = "select_option"
TOOL_STATISTICS = "statistics"
TOOL_NOTIFY = "notify"
TOOL_CALENDAR_CREATE = "calendar_create"
TOOL_MEDIA_SOURCE = "media_source"
TOOL_WEATHER_FORECAST = "weather_forecast"
ALL_TOOLS = [
    TOOL_CLIMATE_MODES,
    TOOL_SELECT_OPTION,
    TOOL_STATISTICS,
    TOOL_NOTIFY,
    TOOL_CALENDAR_CREATE,
    TOOL_MEDIA_SOURCE,
    TOOL_WEATHER_FORECAST,
]
