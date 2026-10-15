# LLM Toolbox

A Home Assistant integration that adds extra tools to the **Assist LLM API**, so every conversation
agent can do more: OpenAI, Anthropic, Google Gemini, Ollama, or any custom agent that uses the Assist API.

It has no conversation agent of its own and no Python dependencies.

## Why

The agents can only do what the Assist LLM API tools allow, and the model cannot call arbitrary
services. As of Home Assistant 2026.10 the built-in tools cover turning things on and off, positions,
target temperature, light/fan/humidifier settings, vacuums, media controls, timers, todo lists,
exposed scripts, current states (`GetLiveContext`) and calendar events for today or this week.
That leaves common requests out:

| You ask | Built-in tools | LLM Toolbox |
|---|---|---|
| "Put the AC in dry mode", "boost the heating" | only the target temperature | `llm_toolbox__climate_set_mode` |
| "Set the robot to mop only", washing machine program | nothing for `select` entities | `llm_toolbox__select_option` |
| "How much energy did we use yesterday / in August?" | current states only | `llm_toolbox__get_statistics` |
| "Will it rain tomorrow?" | current weather only | `llm_toolbox__weather_forecast` |
| "Tell Anna I'm running late" | no notifications | `llm_toolbox__notify` |
| "Add the dentist on Tuesday at 10" | no calendar writes | `llm_toolbox__calendar_create_event` |
| "Play it in the kitchen" | no output/source selection | `llm_toolbox__media_select_source` |

## Tools

| Tool | What it does | Offered when |
|---|---|---|
| `climate_set_mode` | hvac / fan / preset mode; the modes of every device are listed for the model | a `climate` entity is exposed |
| `select_option` | change the option of a `select` entity (mop mode, appliance program...) | a `select` entity is exposed |
| `get_statistics` | recorder long-term statistics per hour/day/week/month (energy, temperature...) | a `sensor` is exposed and the recorder is running |
| `weather_forecast` | daily or hourly forecast | a `weather` entity is exposed |
| `notify` | send a message through a `notify` entity | a `notify` entity is exposed |
| `calendar_create_event` | create a timed or all-day event | a `calendar` is exposed |
| `media_select_source` | move playback to a speaker/device (Spotify Connect and similar) | an exposed `media_player` has sources |

Tools only see entities **exposed to Assist** (Settings → Voice assistants → Expose). That includes
notification targets: expose the `notify` entities the assistant may message.

You choose which tools are enabled when you add the integration (all of them are selected by default),
and you can change the selection at any time with **Configure** on the integration's page.

## Installation

1. HACS → Integrations → ⋮ → Custom repositories → add this repository (category *Integration*), then
   install **LLM Toolbox**. Or copy `custom_components/llm_toolbox` into `config/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **LLM Toolbox**, then pick the tools to enable.
4. Make sure your conversation agent is allowed to control Home Assistant with the **Assist** API.

Requires Home Assistant 2026.10 or newer.

## Development

```powershell
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe pytest-homeassistant-custom-component==0.13.371 `
  hassil==3.12.1 home-assistant-intents==2026.10.6 gazetteer-matcher==1.1.0
.venv/Scripts/python.exe -m pytest
```

On Windows, Home Assistant's test tooling also needs small `fcntl.py` and `resource.py` stub modules in
`.venv/Lib/site-packages` (Linux and CI don't).
