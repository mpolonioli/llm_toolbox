"""Generic tool to change the option of an exposed select entity."""

from __future__ import annotations

from typing import override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .common import ToolboxTool, exposed_states, match_targets, pick_option

SELECT_DOMAIN = "select"


class SelectOptionTool(ToolboxTool):
    """Set the option of a select entity (vacuum mop mode, appliance program...)."""

    name = "llm_toolbox__select_option"

    def __init__(self, states: list[State]) -> None:
        """Build the description from the exposed select entities."""
        lines = [
            f"- {state.name}: {', '.join(map(str, state.attributes.get('options') or []))}"
            for state in states
        ]
        self.description = (
            "Change the selected option of a setting (select entity), for example the "
            "vacuum mop intensity or an appliance program. Available settings and options:\n"
            + "\n".join(lines)
        )
        self.parameters = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Optional("area"): str,
                vol.Required("option"): str,
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Select the option."""
        data = self.parameters(tool_input.tool_args)
        states, error = match_targets(
            hass, llm_context, name=data["name"], area=data.get("area"), domains=[SELECT_DOMAIN]
        )
        if error:
            return error

        applied = []
        for state in states:
            option = pick_option(data["option"], state.attributes.get("options") or [])
            if option is None:
                return {
                    "success": False,
                    "error": f"{state.name} has no option '{data['option']}'",
                    "valid_options": state.attributes.get("options") or [],
                }
            await hass.services.async_call(
                SELECT_DOMAIN,
                "select_option",
                {"entity_id": state.entity_id, "option": option},
                context=llm_context.context,
                blocking=True,
            )
            applied.append({"name": state.name, "option": option})
        return {"success": True, "action": True, "result": applied}


def select_tools(hass: HomeAssistant, llm_context: LLMContext) -> list[Tool]:
    """Return the select tool when select entities are exposed."""
    states = exposed_states(hass, llm_context.assistant, SELECT_DOMAIN)
    return [SelectOptionTool(states)] if states else []
