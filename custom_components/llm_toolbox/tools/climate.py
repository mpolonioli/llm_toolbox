"""Climate tool: hvac, fan and preset modes of thermostats and air conditioners."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from ..const import TOOL_CLIMATE_MODES
from .common import ToolboxTool, exposed_states, match_targets, pick_option

CLIMATE_DOMAIN = "climate"

MODE_ATTRS = {
    "hvac_mode": ("hvac_modes", "set_hvac_mode"),
    "fan_mode": ("fan_modes", "set_fan_mode"),
    "preset_mode": ("preset_modes", "set_preset_mode"),
}


def _modes_summary(states: list[State]) -> str:
    """Group climate entities by their available modes for a compact description."""
    groups: dict[tuple, list[str]] = {}
    for state in states:
        key = tuple(
            (mode, tuple(state.attributes.get(attr) or ()))
            for mode, (attr, _) in MODE_ATTRS.items()
        )
        groups.setdefault(key, []).append(state.name)
    lines = []
    for key, names in groups.items():
        modes = "; ".join(f"{mode}: {', '.join(values)}" for mode, values in key if values)
        lines.append(f"- {', '.join(names)} -> {modes}")
    return "\n".join(lines)


class ClimateSetModeTool(ToolboxTool):
    """Change hvac / fan / preset mode of a thermostat or air conditioner."""

    name = "llm_toolbox__climate_set_mode"

    def __init__(self, states: list[State]) -> None:
        """Build the description from the exposed climate entities."""
        self.description = (
            "Change the operating mode of a thermostat or air conditioner: hvac_mode "
            "(off/heat/cool/dry/fan_only/auto), fan_mode or preset_mode. Use "
            "intent__HassTurnOn/HassTurnOff only to switch a unit on or off and "
            "climate__HassClimateSetTemperature for the target temperature. "
            "Available modes per device:\n" + _modes_summary(states)
        )
        self.parameters = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Optional("area"): str,
                vol.Optional("hvac_mode"): str,
                vol.Optional("fan_mode"): str,
                vol.Optional("preset_mode"): str,
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Apply the requested modes."""
        data = self.parameters(tool_input.tool_args)
        wanted = {mode: data[mode] for mode in MODE_ATTRS if data.get(mode)}
        if not wanted:
            return {
                "success": False,
                "error": "Give at least one of hvac_mode, fan_mode, preset_mode",
            }

        states, error = match_targets(
            hass, llm_context, name=data["name"], area=data.get("area"), domains=[CLIMATE_DOMAIN]
        )
        if error:
            return error

        applied: list[dict[str, Any]] = []
        for state in states:
            changes: dict[str, str] = {}
            for mode, value in wanted.items():
                attr, service = MODE_ATTRS[mode]
                option = pick_option(value, state.attributes.get(attr) or [])
                if option is None:
                    return {
                        "success": False,
                        "error": f"{state.name} does not support {mode} '{value}'",
                        f"valid_{mode}s": state.attributes.get(attr) or [],
                    }
                await hass.services.async_call(
                    CLIMATE_DOMAIN,
                    service,
                    {"entity_id": state.entity_id, mode: option},
                    context=llm_context.context,
                    blocking=True,
                )
                changes[mode] = option
            applied.append({"name": state.name, **changes})
        return {"success": True, "action": True, "result": applied}


def climate_tools(hass: HomeAssistant, llm_context: LLMContext, enabled: set[str]) -> list[Tool]:
    """Return the climate mode tool when climate entities are exposed."""
    if TOOL_CLIMATE_MODES not in enabled:
        return []
    states = exposed_states(hass, llm_context.assistant, CLIMATE_DOMAIN)
    return [ClimateSetModeTool(states)] if states else []
