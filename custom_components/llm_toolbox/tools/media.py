"""Tool to move playback to a specific speaker (media player source)."""

from __future__ import annotations

from typing import override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .common import ToolboxTool, exposed_states, match_targets, pick_option

MEDIA_DOMAIN = "media_player"


def _sources(state: State) -> list[str]:
    return [str(source) for source in state.attributes.get("source_list") or [] if source]


class MediaSelectSourceTool(ToolboxTool):
    """Select the output device / source of a media player."""

    name = "llm_toolbox__media_select_source"

    def __init__(self, states: list[State]) -> None:
        """Build the description with players and their sources."""
        lines = [f"- {state.name}: {', '.join(_sources(state))}" for state in states]
        self.description = (
            "Choose on which speaker or device a media player plays (its source), for "
            "example a Spotify Connect device. Use it before "
            "media_player__HassMediaSearchAndPlay when the user wants music in a "
            "specific room; pick the source that matches the room, defaulting to the room "
            "the request comes from. Players and sources:\n" + "\n".join(lines)
        )
        self.parameters = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("source"): str,
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Select the source."""
        data = self.parameters(tool_input.tool_args)
        states, error = match_targets(hass, llm_context, name=data["name"], domains=[MEDIA_DOMAIN])
        if error:
            return error
        state = states[0]
        source = pick_option(data["source"], _sources(state))
        if source is None:
            return {
                "success": False,
                "error": f"{state.name} has no source '{data['source']}'",
                "valid_sources": _sources(state),
            }
        await hass.services.async_call(
            MEDIA_DOMAIN,
            "select_source",
            {"entity_id": state.entity_id, "source": source},
            context=llm_context.context,
            blocking=True,
        )
        return {"success": True, "action": True, "result": {"name": state.name, "source": source}}


def media_tools(hass: HomeAssistant, llm_context: LLMContext) -> list[Tool]:
    """Return the source tool when an exposed player has selectable sources."""
    states = [
        state
        for state in exposed_states(hass, llm_context.assistant, MEDIA_DOMAIN)
        if _sources(state)
    ]
    return [MediaSelectSourceTool(states)] if states else []
