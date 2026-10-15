"""Shared helpers for the LLM Toolbox tools."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from operator import attrgetter

from homeassistant.components.homeassistant import async_should_expose
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent
from homeassistant.helpers.llm import LLMContext, Tool, ToolInput, ToolResult
from homeassistant.util.json import JsonObjectType

from ..const import DOMAIN


class ToolboxTool(Tool):
    """Tool whose result payload marks a failure with ``"success": False``."""

    integration = DOMAIN

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> ToolResult:
        """Call the tool and wrap its payload in a ToolResult."""
        data = await self.async_run(hass, tool_input, llm_context)
        return ToolResult(data=data, error=data.get("success") is False)

    async def async_run(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Run the tool and return its JSON payload."""
        raise NotImplementedError


def exposed_states(hass: HomeAssistant, assistant: str, domain: str) -> list[State]:
    """Return the states of ``domain`` exposed to the assistant, sorted by name."""
    return [
        state
        for state in sorted(hass.states.async_all(domain), key=attrgetter("name"))
        if async_should_expose(hass, assistant, state.entity_id)
    ]


def match_targets(
    hass: HomeAssistant,
    llm_context: LLMContext,
    *,
    name: str | None,
    area: str | None = None,
    domains: Collection[str],
    features: int | None = None,
) -> tuple[list[State], JsonObjectType | None]:
    """Resolve exposed entities by name / area like the built-in intents do.

    Returns the matched states, or an error payload the model can act on.
    """
    constraints = intent.MatchTargetsConstraints(
        name=name or None,
        area_name=area or None,
        domains=domains,
        features=features,
        assistant=llm_context.assistant,
        allow_duplicate_names=True,
    )
    preferences = None
    if llm_context.device_id and (device := dr.async_get(hass).async_get(llm_context.device_id)):
        preferences = intent.MatchTargetsPreferences(area_id=device.area_id)

    result = intent.async_match_targets(hass, constraints, preferences)
    if result.is_match:
        return result.states, None

    reason = result.no_match_reason.name.lower() if result.no_match_reason else "unknown"
    candidates = [
        state.name
        for domain in domains
        for state in exposed_states(hass, llm_context.assistant, domain)
    ]
    return [], {
        "success": False,
        "error": f"No matching entity ({reason})",
        "candidates": candidates[:40],
    }


def pick_option(value: str, options: Iterable[str]) -> str | None:
    """Match a user supplied option against the entity's options, case-insensitively."""
    wanted = value.strip().lower()
    for option in options:
        lowered = str(option).lower()
        if wanted in (lowered, lowered.replace("_", " ")):
            return str(option)
    return None
