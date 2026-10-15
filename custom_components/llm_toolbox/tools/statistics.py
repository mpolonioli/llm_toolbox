"""Tool exposing recorder long-term statistics (energy history etc.)."""

from __future__ import annotations

from typing import Any, cast, override

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonObjectType

from .common import ToolboxTool, exposed_states, match_targets

SENSOR_DOMAIN = "sensor"
PERIODS = ["hour", "day", "week", "month"]
TYPES = ["change", "mean", "min", "max", "sum", "state"]
MAX_ROWS = 60


class GetStatisticsTool(ToolboxTool):
    """Query recorder statistics for an exposed sensor."""

    name = "llm_toolbox__get_statistics"
    description = (
        "Get historical statistics of a sensor (energy consumed or produced, power, "
        "temperature...) aggregated per hour, day, week or month between start_time and "
        "end_time (local ISO datetimes, e.g. 2026-09-16T00:00:00). Use it for questions "
        "about yesterday, last week, this month, a given day. Each row reports what the "
        "sensor supports: 'change' is the amount accumulated in that period (use it for "
        "energy counters, including daily/weekly/monthly meters), 'mean'/'min'/'max' apply "
        "to measurements such as power, temperature or humidity. Only exposed sensors can "
        "be queried."
    )
    parameters = vol.Schema(
        {
            vol.Required("name"): str,
            vol.Required("start_time"): str,
            vol.Optional("end_time"): str,
            vol.Required("period"): vol.In(PERIODS),
        }
    )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Fetch the statistics."""
        data = self.parameters(tool_input.tool_args)
        states, error = match_targets(hass, llm_context, name=data["name"], domains=[SENSOR_DOMAIN])
        if error:
            return error
        state = states[0]

        start = dt_util.parse_datetime(data["start_time"])
        if start is None:
            return {"success": False, "error": "start_time is not a valid ISO datetime"}
        if start.tzinfo is None:
            start = dt_util.as_utc(start.replace(tzinfo=dt_util.get_default_time_zone()))
        service_data: dict[str, Any] = {
            "statistic_ids": [state.entity_id],
            "start_time": dt_util.as_local(start).strftime("%Y-%m-%d %H:%M:%S"),
            "period": data["period"],
            "types": TYPES,
        }
        if data.get("end_time"):
            end = dt_util.parse_datetime(data["end_time"])
            if end is None:
                return {"success": False, "error": "end_time is not a valid ISO datetime"}
            if end.tzinfo is None:
                end = dt_util.as_utc(end.replace(tzinfo=dt_util.get_default_time_zone()))
            service_data["end_time"] = dt_util.as_local(end).strftime("%Y-%m-%d %H:%M:%S")

        response = await hass.services.async_call(
            "recorder",
            "get_statistics",
            service_data,
            context=llm_context.context,
            blocking=True,
            return_response=True,
        )
        rows = cast(dict, response).get("statistics", {}).get(state.entity_id, [])
        result = []
        for row in rows[:MAX_ROWS]:
            item: dict[str, Any] = {}
            for key, value in row.items():
                if key in ("start", "end"):
                    parsed = dt_util.parse_datetime(str(value))
                    item[key] = (
                        dt_util.as_local(parsed).isoformat(timespec="minutes") if parsed else value
                    )
                elif isinstance(value, float):
                    item[key] = round(value, 3)
                elif value is not None:
                    item[key] = value
            result.append(item)

        return {
            "success": True,
            "entity": state.name,
            "unit": str(unit) if (unit := state.attributes.get("unit_of_measurement")) else None,
            "period": data["period"],
            "rows": result,
            "truncated": len(rows) > MAX_ROWS,
        }


def statistics_tools(hass: HomeAssistant, llm_context: LLMContext) -> list[Tool]:
    """Return the statistics tool when sensors are exposed and the recorder is loaded."""
    if not hass.services.has_service("recorder", "get_statistics"):
        return []
    if not exposed_states(hass, llm_context.assistant, SENSOR_DOMAIN):
        return []
    return [GetStatisticsTool()]
