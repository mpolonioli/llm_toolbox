"""LLM tools platform: contributes the toolbox to the Assist LLM API.

Home Assistant's ``llm`` integration discovers this module and calls
``async_get_tools`` for every conversation request, so the tools are available
to any agent using the Assist API (OpenAI, Anthropic, Google, Ollama...) and
show up in conversation traces.
"""

from __future__ import annotations

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLM_API_ASSIST, LLMContext, Tool

from .const import (
    ALL_TOOLS,
    CONF_TOOLS,
    DOMAIN,
    TOOL_MEDIA_SOURCE,
    TOOL_NOTIFY,
    TOOL_SELECT_OPTION,
    TOOL_STATISTICS,
    TOOL_WEATHER_FORECAST,
)
from .tools.calendar import calendar_tools
from .tools.climate import climate_tools
from .tools.media import media_tools
from .tools.notify import notify_tools
from .tools.select import select_tools
from .tools.statistics import statistics_tools
from .tools.weather import weather_tools

# Steers the model to our tools for questions the built-in ones cannot answer.
PROMPTS = {
    f"{DOMAIN}__get_statistics": (
        f"Use {DOMAIN}__get_statistics for questions about past energy, consumption, "
        "production or measurements (yesterday, last week, this month)."
    ),
    f"{DOMAIN}__weather_forecast": f"Use {DOMAIN}__weather_forecast for future weather.",
    f"{DOMAIN}__notify": f"Use {DOMAIN}__notify to send a message to a person or device.",
}


@callback
def _enabled_tools(hass: HomeAssistant) -> set[str]:
    """Return the tool ids enabled in the integration options."""
    enabled: set[str] = set()
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        enabled.update(entry.options.get(CONF_TOOLS, ALL_TOOLS))
    return enabled


@callback
def async_get_tools(hass: HomeAssistant, llm_context: LLMContext, api_id: str) -> LLMTools | None:
    """Return the enabled tools whose entities are exposed to the assistant."""
    if api_id != LLM_API_ASSIST:
        return None
    enabled = _enabled_tools(hass)
    if not enabled:
        return None

    tools: list[Tool] = []
    tools.extend(climate_tools(hass, llm_context, enabled))
    if TOOL_SELECT_OPTION in enabled:
        tools.extend(select_tools(hass, llm_context))
    if TOOL_STATISTICS in enabled:
        tools.extend(statistics_tools(hass, llm_context))
    if TOOL_NOTIFY in enabled:
        tools.extend(notify_tools(hass, llm_context))
    tools.extend(calendar_tools(hass, llm_context, enabled))
    if TOOL_MEDIA_SOURCE in enabled:
        tools.extend(media_tools(hass, llm_context))
    if TOOL_WEATHER_FORECAST in enabled:
        tools.extend(weather_tools(hass, llm_context))

    if not tools:
        return None
    prompts = [PROMPTS[tool.name] for tool in tools if tool.name in PROMPTS]
    return LLMTools(tools=tools, prompt=" ".join(prompts) or None)
