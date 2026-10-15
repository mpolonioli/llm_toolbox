"""Tests for the LLM Toolbox config and options flows."""

from __future__ import annotations

from custom_components.llm_toolbox.const import ALL_TOOLS, CONF_TOOLS, DOMAIN, TITLE
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_user_flow_picks_tools(hass: HomeAssistant) -> None:
    """Setup offers every tool, pre-selected, and stores the user's choice."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    field = next(iter(result["data_schema"].schema))
    assert field == CONF_TOOLS
    assert field.default() == ALL_TOOLS

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOOLS: ["climate_modes", "notify"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {}
    assert result["options"] == {CONF_TOOLS: ["climate_modes", "notify"]}


async def test_user_flow_with_every_tool_off(hass: HomeAssistant) -> None:
    """Deselecting everything is allowed: the integration then offers no tools."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOOLS: []})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {CONF_TOOLS: []}


async def test_single_instance(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """A second entry is refused."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow_selects_tools(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The options flow stores the chosen tools."""
    hass.config_entries.async_update_entry(init_integration, options={CONF_TOOLS: ["notify"]})
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # The form starts from the current selection.
    assert next(iter(result["data_schema"].schema)).default() == ["notify"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TOOLS: ["notify", "weather_forecast"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.options == {CONF_TOOLS: ["notify", "weather_forecast"]}


async def test_unload(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    assert init_integration.state is config_entries.ConfigEntryState.NOT_LOADED
