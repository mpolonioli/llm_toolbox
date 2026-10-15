"""Tool to send notifications to phones, chats and displays."""

from __future__ import annotations

from typing import override

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .common import ToolboxTool, exposed_states

NOTIFY_DOMAIN = "notify"


class NotifyTool(ToolboxTool):
    """Send a message through a notify entity."""

    name = "llm_toolbox__notify"

    def __init__(self, states: list[State]) -> None:
        """Build the target list from the notify entities."""
        self._by_name = {state.name.lower(): state.entity_id for state in states}
        self.description = (
            "Send a text message to a person's phone, a chat or a display. "
            "Use it when asked to send, notify, remind or tell someone something. "
            "Available targets: " + ", ".join(state.name for state in states)
        )
        self.parameters = vol.Schema(
            {
                vol.Required("target"): vol.In([state.name for state in states]),
                vol.Required("message"): str,
                vol.Optional("title"): str,
            }
        )

    @override
    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Send the message."""
        data = self.parameters(tool_input.tool_args)
        entity_id = self._by_name[data["target"].lower()]
        service_data = {"entity_id": entity_id, "message": data["message"]}
        if data.get("title"):
            service_data["title"] = data["title"]
        await hass.services.async_call(
            NOTIFY_DOMAIN,
            "send_message",
            service_data,
            context=llm_context.context,
            blocking=True,
        )
        return {
            "success": True,
            "action": True,
            "result": {"target": data["target"], "message": data["message"]},
        }


def notify_tools(hass: HomeAssistant, llm_context: LLMContext) -> list[Tool]:
    """Return the notify tool when notify entities are exposed.

    Only exposed targets are offered, so the model cannot message a device
    the user did not opt in.
    """
    states = exposed_states(hass, llm_context.assistant, NOTIFY_DOMAIN)
    return [NotifyTool(states)] if states else []
