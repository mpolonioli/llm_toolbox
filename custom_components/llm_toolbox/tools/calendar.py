"""Tool to create calendar events."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonObjectType

from ..const import TOOL_CALENDAR_CREATE
from .common import ToolboxTool, exposed_states, match_targets

CALENDAR_DOMAIN = "calendar"


class CalendarCreateEventTool(ToolboxTool):
    """Create an event on an exposed calendar."""

    name = "llm_toolbox__calendar_create_event"

    def __init__(self, states: list[State]) -> None:
        """Build the calendar list."""
        self.description = (
            "Create an event on a calendar. start/end are local ISO datetimes "
            "(2026-09-20T18:30:00) or dates (2026-09-20) for all-day events; end defaults "
            "to one hour after start (next day for all-day). Calendars: "
            + ", ".join(state.name for state in states)
        )
        self.parameters = vol.Schema(
            {
                vol.Required("calendar"): vol.In([state.name for state in states]),
                vol.Required("summary"): str,
                vol.Required("start"): str,
                vol.Optional("end"): str,
                vol.Optional("description"): str,
                vol.Optional("location"): str,
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Create the event."""
        data = self.parameters(tool_input.tool_args)
        states, error = match_targets(
            hass, llm_context, name=data["calendar"], domains=[CALENDAR_DOMAIN]
        )
        if error:
            return error
        entity_id = states[0].entity_id

        service_data: dict[str, Any] = {"entity_id": entity_id, "summary": data["summary"]}
        for key in ("description", "location"):
            if data.get(key):
                service_data[key] = data[key]

        if "T" in data["start"]:
            start = dt_util.parse_datetime(data["start"])
            if start is None:
                return {"success": False, "error": "start is not a valid ISO datetime"}
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt_util.get_default_time_zone())
            end = dt_util.parse_datetime(data["end"]) if data.get("end") else None
            if end is None:
                end = start + timedelta(hours=1)
            elif end.tzinfo is None:
                end = end.replace(tzinfo=dt_util.get_default_time_zone())
            service_data["start_date_time"] = dt_util.as_local(start).strftime("%Y-%m-%d %H:%M:%S")
            service_data["end_date_time"] = dt_util.as_local(end).strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_date = dt_util.parse_date(data["start"])
            if start_date is None:
                return {"success": False, "error": "start is not a valid ISO date"}
            end_date = dt_util.parse_date(data["end"]) if data.get("end") else None
            if end_date is None:
                end_date = start_date + timedelta(days=1)
            service_data["start_date"] = start_date.isoformat()
            service_data["end_date"] = end_date.isoformat()

        await hass.services.async_call(
            CALENDAR_DOMAIN,
            "create_event",
            service_data,
            context=llm_context.context,
            blocking=True,
        )
        return {
            "success": True,
            "action": True,
            "result": {k: v for k, v in service_data.items() if k != "entity_id"},
        }


def calendar_tools(hass: HomeAssistant, llm_context: LLMContext, enabled: set[str]) -> list[Tool]:
    """Return the event creation tool when calendars are exposed."""
    if TOOL_CALENDAR_CREATE not in enabled:
        return []
    states = exposed_states(hass, llm_context.assistant, CALENDAR_DOMAIN)
    return [CalendarCreateEventTool(states)] if states else []
