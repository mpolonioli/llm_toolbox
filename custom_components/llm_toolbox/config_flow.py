"""Config flow for the LLM Toolbox integration."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import ALL_TOOLS, CONF_TOOLS, DOMAIN, TITLE


def _tools_schema(enabled: list[str]) -> vol.Schema:
    """Return the tools multi-select, pre-filled with the enabled tools."""
    return vol.Schema(
        {
            vol.Optional(CONF_TOOLS, default=enabled): SelectSelector(
                SelectSelectorConfig(
                    options=ALL_TOOLS,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_TOOLS,
                )
            )
        }
    )


class LLMToolboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single entry with the tools picked by the user."""

    VERSION = 1
    MINOR_VERSION = 1

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick the tools to offer; every tool is selected by default."""
        if user_input is not None:
            return self.async_create_entry(
                title=TITLE, data={}, options={CONF_TOOLS: user_input.get(CONF_TOOLS, [])}
            )
        return self.async_show_form(step_id="user", data_schema=_tools_schema(ALL_TOOLS))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow (which tools are offered)."""
        return LLMToolboxOptionsFlow()


class LLMToolboxOptionsFlow(OptionsFlow):
    """Pick the tools offered to conversation agents."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the tools multi-select."""
        if user_input is not None:
            return self.async_create_entry(data={CONF_TOOLS: user_input.get(CONF_TOOLS, [])})

        return self.async_show_form(
            step_id="init",
            data_schema=_tools_schema(self.config_entry.options.get(CONF_TOOLS, ALL_TOOLS)),
        )
