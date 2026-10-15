"""Tool exposing weather forecasts."""

from __future__ import annotations

from typing import Any, cast, override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonObjectType

from .common import ToolboxTool, exposed_states, match_targets

WEATHER_DOMAIN = "weather"
KEEP_KEYS = (
    "datetime",
    "condition",
    "temperature",
    "templow",
    "precipitation",
    "precipitation_probability",
    "wind_speed",
    "humidity",
)
LIMITS = {"daily": 6, "hourly": 12}


class WeatherForecastTool(ToolboxTool):
    """Return the daily or hourly forecast of a weather entity."""

    name = "llm_toolbox__weather_forecast"

    def __init__(self, states: list[State]) -> None:
        """Build the description with the exposed weather entities."""
        self.description = (
            "Get the weather forecast: 'daily' for the next days, 'hourly' for the next "
            "hours. Use it for any question about future weather (tomorrow, this weekend, "
            "will it rain later). Weather entities: " + ", ".join(state.name for state in states)
        )
        self.parameters = vol.Schema(
            {
                vol.Optional("name"): str,
                vol.Required("type", default="daily"): vol.In(list(LIMITS)),
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Fetch the forecast."""
        data = self.parameters(tool_input.tool_args)
        if data.get("name"):
            states, error = match_targets(
                hass, llm_context, name=data["name"], domains=[WEATHER_DOMAIN]
            )
            if error:
                return error
        else:
            states = exposed_states(hass, llm_context.assistant, WEATHER_DOMAIN)
            if not states:
                return {"success": False, "error": "No weather entity exposed"}
        state = states[0]

        response = await hass.services.async_call(
            WEATHER_DOMAIN,
            "get_forecasts",
            {"entity_id": state.entity_id, "type": data["type"]},
            context=llm_context.context,
            blocking=True,
            return_response=True,
        )
        forecast = cast(dict, response).get(state.entity_id, {}).get("forecast", [])
        rows: list[dict[str, Any]] = []
        for item in forecast[: LIMITS[data["type"]]]:
            row = {key: item[key] for key in KEEP_KEYS if item.get(key) is not None}
            if parsed := dt_util.parse_datetime(str(item.get("datetime", ""))):
                row["datetime"] = dt_util.as_local(parsed).isoformat(timespec="minutes")
            rows.append(row)
        return {
            "success": True,
            "entity": state.name,
            "type": data["type"],
            "temperature_unit": state.attributes.get("temperature_unit"),
            "forecast": rows,
        }


def weather_tools(hass: HomeAssistant, llm_context: LLMContext) -> list[Tool]:
    """Return the forecast tool when a weather entity is exposed."""
    states = exposed_states(hass, llm_context.assistant, WEATHER_DOMAIN)
    return [WeatherForecastTool(states)] if states else []
