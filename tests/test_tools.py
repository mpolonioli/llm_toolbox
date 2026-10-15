"""Tests for the LLM Toolbox tools platform."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.llm_toolbox.const import CONF_TOOLS, DOMAIN
from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.core import Context, HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

ASSISTANT = "conversation"


def _context() -> llm.LLMContext:
    return llm.LLMContext(
        platform=DOMAIN, context=Context(), language="en", assistant=ASSISTANT, device_id=None
    )


async def _tools(hass: HomeAssistant) -> llm.APIInstance:
    return await llm.async_get_api(hass, llm.LLM_API_ASSIST, _context())


def _names(api: llm.APIInstance) -> set[str]:
    return {tool.name for tool in api.tools if tool.name.startswith("llm_toolbox__")}


async def _call(hass: HomeAssistant, tool_name: str, **args: Any) -> Any:
    api = await _tools(hass)
    result = await api.async_call_tool(llm.ToolInput(tool_name=tool_name, tool_args=args))
    assert result.error is (result.data.get("success") is False)
    return result.data


def _expose(hass: HomeAssistant, entity_id: str, state: str, **attributes: Any) -> None:
    hass.states.async_set(entity_id, state, attributes)
    async_expose_entity(hass, ASSISTANT, entity_id, True)


@pytest.fixture
async def house(hass: HomeAssistant, init_integration: MockConfigEntry) -> MockConfigEntry:
    """Expose a small house: AC, select, calendar, player, weather, sensor, phone."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    _expose(
        hass,
        "climate.bedroom_air_conditioner",
        "off",
        friendly_name="Bedroom Air Conditioner",
        hvac_modes=["off", "cool", "dry", "heat"],
        fan_modes=["auto", "low", "high"],
        preset_modes=["none", "wind_free", "quiet"],
    )
    _expose(
        hass,
        "select.vacuum_mop_intensity",
        "high",
        friendly_name="Mop intensity",
        options=["off", "low", "medium", "high"],
    )
    _expose(hass, "calendar.family", "off", friendly_name="Family Calendar")
    _expose(
        hass,
        "media_player.music",
        "idle",
        friendly_name="Music",
        source_list=["", "Kitchen Speaker", "Living Room Speaker"],
    )
    _expose(hass, "weather.home", "cloudy", friendly_name="Home", temperature_unit="°C")
    _expose(
        hass,
        "sensor.consumption_energy",
        "1234.5",
        friendly_name="Consumption Energy",
        unit_of_measurement="kWh",
    )
    _expose(hass, "notify.anna_phone", "unknown", friendly_name="Anna's Phone")
    # Not exposed: must never be offered as a target.
    hass.states.async_set("notify.office_display", "unknown", {"friendly_name": "Office Display"})
    hass.services.async_register(
        "recorder",
        "get_statistics",
        lambda call: {"statistics": {}},
        supports_response=SupportsResponse.ONLY,
    )
    return init_integration


async def test_tools_registered(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Every tool shows up once its entities are exposed."""
    assert _names(await _tools(hass)) == {
        "llm_toolbox__climate_set_mode",
        "llm_toolbox__select_option",
        "llm_toolbox__get_statistics",
        "llm_toolbox__notify",
        "llm_toolbox__calendar_create_event",
        "llm_toolbox__media_select_source",
        "llm_toolbox__weather_forecast",
    }
    api = await _tools(hass)
    assert "llm_toolbox__get_statistics" in api.api_prompt
    mode_tool = next(t for t in api.tools if t.name == "llm_toolbox__climate_set_mode")
    assert "Bedroom Air Conditioner -> hvac_mode: off, cool, dry, heat" in mode_tool.description


async def test_tools_can_be_disabled(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """The options flow selection filters the tools."""
    hass.config_entries.async_update_entry(house, options={CONF_TOOLS: ["notify"]})
    await hass.async_block_till_done()
    assert _names(await _tools(hass)) == {"llm_toolbox__notify"}


async def test_no_tools_without_exposed_entities(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Nothing is offered until matching entities are exposed."""
    hass.states.async_set("notify.anna_phone", "unknown", {"friendly_name": "Anna's Phone"})
    assert _names(await _tools(hass)) == set()


async def test_tools_gone_after_unload(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Unloading the entry removes the tools from every agent."""
    assert await hass.config_entries.async_unload(house.entry_id)
    assert _names(await _tools(hass)) == set()


async def test_notify_offers_only_exposed_targets(
    hass: HomeAssistant, house: MockConfigEntry
) -> None:
    """A notify entity that is not exposed cannot be messaged."""
    api = await _tools(hass)
    tool = next(t for t in api.tools if t.name == "llm_toolbox__notify")
    assert "Anna's Phone" in tool.description
    assert "Office Display" not in tool.description


async def test_climate_set_mode(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Modes are validated and applied through the climate services."""
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    preset = async_mock_service(hass, "climate", "set_preset_mode")

    result = await _call(
        hass,
        "llm_toolbox__climate_set_mode",
        name="Bedroom Air Conditioner",
        hvac_mode="Cool",
        preset_mode="wind free",
    )
    assert result["success"] is True
    assert hvac[0].data == {"entity_id": "climate.bedroom_air_conditioner", "hvac_mode": "cool"}
    assert preset[0].data == {
        "entity_id": "climate.bedroom_air_conditioner",
        "preset_mode": "wind_free",
    }

    result = await _call(
        hass, "llm_toolbox__climate_set_mode", name="Bedroom Air Conditioner", fan_mode="turbo"
    )
    assert result["success"] is False
    assert result["valid_fan_modes"] == ["auto", "low", "high"]

    result = await _call(hass, "llm_toolbox__climate_set_mode", name="Garage", hvac_mode="cool")
    assert result["success"] is False
    assert "Bedroom Air Conditioner" in result["candidates"]


async def test_select_option(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Options are matched case-insensitively."""
    calls = async_mock_service(hass, "select", "select_option")
    result = await _call(hass, "llm_toolbox__select_option", name="Mop intensity", option="Low")
    assert result["success"] is True
    assert calls[0].data == {"entity_id": "select.vacuum_mop_intensity", "option": "low"}

    result = await _call(hass, "llm_toolbox__select_option", name="Mop intensity", option="max")
    assert result["success"] is False
    assert result["valid_options"] == ["off", "low", "medium", "high"]


async def test_notify(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Messages go through notify.send_message on the chosen entity."""
    calls = async_mock_service(hass, "notify", "send_message")
    result = await _call(
        hass,
        "llm_toolbox__notify",
        target="Anna's Phone",
        message="Buy bread",
        title="Home",
    )
    assert result["success"] is True
    assert calls[0].data == {
        "entity_id": "notify.anna_phone",
        "message": "Buy bread",
        "title": "Home",
    }


async def test_calendar_create_event(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Timed and all-day events are created with the right fields."""
    calls = async_mock_service(hass, "calendar", "create_event")
    result = await _call(
        hass,
        "llm_toolbox__calendar_create_event",
        calendar="Family Calendar",
        summary="Dentist",
        start="2026-09-20T10:00:00",
    )
    assert result["success"] is True
    assert calls[0].data == {
        "entity_id": "calendar.family",
        "summary": "Dentist",
        "start_date_time": "2026-09-20 10:00:00",
        "end_date_time": "2026-09-20 11:00:00",
    }

    await _call(
        hass,
        "llm_toolbox__calendar_create_event",
        calendar="Family Calendar",
        summary="Holiday",
        start="2026-09-21",
        end="2026-09-25",
    )
    assert calls[1].data["start_date"] == "2026-09-21"
    assert calls[1].data["end_date"] == "2026-09-25"


async def test_media_select_source(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """The source is matched against the player's source list."""
    calls = async_mock_service(hass, "media_player", "select_source")
    result = await _call(
        hass, "llm_toolbox__media_select_source", name="Music", source="kitchen speaker"
    )
    assert result["success"] is True
    assert calls[0].data == {"entity_id": "media_player.music", "source": "Kitchen Speaker"}

    result = await _call(
        hass, "llm_toolbox__media_select_source", name="Music", source="Garage Speaker"
    )
    assert result["success"] is False
    assert result["valid_sources"] == ["Kitchen Speaker", "Living Room Speaker"]


async def test_weather_forecast(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Forecast rows are trimmed to the useful keys."""

    async def get_forecasts(call: ServiceCall) -> dict[str, Any]:
        assert call.data["type"] == "daily"
        return {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": "2026-09-18T10:00:00+00:00",
                        "condition": "rainy",
                        "temperature": 21.5,
                        "templow": 14.0,
                        "precipitation": 3.2,
                        "wind_bearing": 180,
                    }
                ]
            }
        }

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    result = await _call(hass, "llm_toolbox__weather_forecast", type="daily")
    assert result["success"] is True
    assert result["entity"] == "Home"
    assert result["forecast"] == [
        {
            "datetime": "2026-09-18T12:00+02:00",
            "condition": "rainy",
            "temperature": 21.5,
            "templow": 14.0,
            "precipitation": 3.2,
        }
    ]


async def test_get_statistics(hass: HomeAssistant, house: MockConfigEntry) -> None:
    """Statistics are requested for the matched sensor and rounded."""
    received: list[ServiceCall] = []

    async def get_statistics(call: ServiceCall) -> dict[str, Any]:
        received.append(call)
        return {
            "statistics": {
                "sensor.consumption_energy": [
                    {
                        "start": "2026-09-16T00:00:00+02:00",
                        "end": "2026-09-17T00:00:00+02:00",
                        "change": 12.93999,
                        "mean": None,
                    }
                ]
            }
        }

    hass.services.async_register(
        "recorder", "get_statistics", get_statistics, supports_response=SupportsResponse.ONLY
    )
    result = await _call(
        hass,
        "llm_toolbox__get_statistics",
        name="Consumption Energy",
        start_time="2026-09-16T00:00:00",
        end_time="2026-09-17T00:00:00",
        period="day",
    )
    assert result["success"] is True
    assert result["unit"] == "kWh"
    assert result["rows"] == [
        {"start": "2026-09-16T00:00+02:00", "end": "2026-09-17T00:00+02:00", "change": 12.94}
    ]
    assert received[0].data == {
        "statistic_ids": ["sensor.consumption_energy"],
        "start_time": "2026-09-16 00:00:00",
        "end_time": "2026-09-17 00:00:00",
        "period": "day",
        "types": ["change", "mean", "min", "max", "sum", "state"],
    }
