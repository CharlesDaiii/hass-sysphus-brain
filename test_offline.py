"""Offline tests for the Sysphus Brain conversation agent logic.

Stubs the small slice of the Home Assistant API that
custom_components/sysphus_brain imports, then exercises:

1. Fast path: built-in agent handles the text -> its result is returned
   verbatim and the brain webhook is never called.
2. Fallthrough: built-in agent returns an error -> the brain webhook's
   reply becomes the spoken response.
3. Fallback: built-in agent errors AND the webhook times out -> the
   canned fallback sentence (Chinese for zh, English for en).

Run: python3 test_offline.py
"""

from __future__ import annotations

import asyncio
import enum
import sys
import types
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# Home Assistant stubs (only what the integration imports)
# --------------------------------------------------------------------------

ha = types.ModuleType("homeassistant")
ha.__path__ = []
components = types.ModuleType("homeassistant.components")
components.__path__ = []
conversation_mod = types.ModuleType("homeassistant.components.conversation")
core_mod = types.ModuleType("homeassistant.core")
config_entries_mod = types.ModuleType("homeassistant.config_entries")
const_mod = types.ModuleType("homeassistant.const")
helpers = types.ModuleType("homeassistant.helpers")
helpers.__path__ = []
intent_mod = types.ModuleType("homeassistant.helpers.intent")
aiohttp_client_mod = types.ModuleType("homeassistant.helpers.aiohttp_client")
entity_platform_mod = types.ModuleType("homeassistant.helpers.entity_platform")
aiohttp_mod = types.ModuleType("aiohttp")


class HomeAssistant:
    pass


class ConfigEntry:
    def __init__(self) -> None:
        self.entry_id = "test-entry-id"
        self.data: dict[str, Any] = {}
        self.options: dict[str, Any] = {}
        self.runtime_data: Any = None


class Platform(enum.Enum):
    CONVERSATION = "conversation"


class IntentResponseType(enum.Enum):
    ACTION_DONE = "action_done"
    QUERY_ANSWER = "query_answer"
    ERROR = "error"


class IntentResponseErrorCode(enum.StrEnum):
    NO_INTENT_MATCH = "no_intent_match"
    UNKNOWN = "unknown"


class IntentResponse:
    def __init__(self, language: str) -> None:
        self.language = language
        self.response_type = IntentResponseType.ACTION_DONE
        self.error_code = None
        self.speech: str | None = None

    def async_set_speech(self, speech: str) -> None:
        self.speech = speech

    def async_set_error(self, code, message: str) -> None:
        self.response_type = IntentResponseType.ERROR
        self.error_code = code
        self.speech = message


@dataclass
class ConversationResult:
    response: IntentResponse
    conversation_id: str | None = None
    continue_conversation: bool = False


@dataclass
class ConversationInput:
    text: str
    context: Any = None
    conversation_id: str | None = "conv-1"
    device_id: str | None = None
    satellite_id: str | None = "assist_satellite.coffee_corner"
    language: str = "zh-CN"
    agent_id: str = "conversation.sysphus"
    extra_system_prompt: str | None = None


class ConversationEntityFeature(enum.IntFlag):
    CONTROL = 1


class ConversationEntity:
    hass: HomeAssistant


class ChatLog:
    pass


class ClientTimeout:
    def __init__(self, total: float | None = None) -> None:
        self.total = total


# Mutable test knobs ---------------------------------------------------------
BUILT_IN_RESULT: ConversationResult | None = None
BUILT_IN_RAISES = False
WEBHOOK_REPLY: dict[str, Any] | None = None
WEBHOOK_RAISES = False
CALLS: dict[str, Any] = {"converse_agent_ids": [], "webhook_posts": []}


async def fake_async_converse(hass, text, conversation_id, context, language,
                              agent_id, device_id, satellite_id):
    CALLS["converse_agent_ids"].append(agent_id)
    if BUILT_IN_RAISES:
        raise RuntimeError("built-in exploded")
    return BUILT_IN_RESULT


class _FakeResponse:
    def raise_for_status(self) -> None:
        pass

    async def json(self) -> Any:
        return WEBHOOK_REPLY


class _FakePostContext:
    async def __aenter__(self) -> _FakeResponse:
        return _FakeResponse()

    async def __aexit__(self, *exc) -> bool:
        return False


class _FakeSession:
    def post(self, url, json, timeout):
        CALLS["webhook_posts"].append({"url": url, "json": json,
                                       "timeout": timeout.total})
        if WEBHOOK_RAISES:
            raise TimeoutError("webhook timed out")
        return _FakePostContext()


def fake_get_clientsession(hass):
    return _FakeSession()


conversation_mod.HOME_ASSISTANT_AGENT = "conversation.home_assistant"
conversation_mod.ConversationEntity = ConversationEntity
conversation_mod.ConversationEntityFeature = ConversationEntityFeature
conversation_mod.ConversationResult = ConversationResult
conversation_mod.ConversationInput = ConversationInput
conversation_mod.ChatLog = ChatLog
conversation_mod.async_converse = fake_async_converse
core_mod.HomeAssistant = HomeAssistant
config_entries_mod.ConfigEntry = ConfigEntry
const_mod.Platform = Platform
intent_mod.IntentResponse = IntentResponse
intent_mod.IntentResponseType = IntentResponseType
intent_mod.IntentResponseErrorCode = IntentResponseErrorCode
aiohttp_client_mod.async_get_clientsession = fake_get_clientsession
entity_platform_mod.AddConfigEntryEntitiesCallback = object
aiohttp_mod.ClientTimeout = ClientTimeout

sys.modules.update({
    "homeassistant": ha,
    "homeassistant.components": components,
    "homeassistant.components.conversation": conversation_mod,
    "homeassistant.core": core_mod,
    "homeassistant.config_entries": config_entries_mod,
    "homeassistant.const": const_mod,
    "homeassistant.helpers": helpers,
    "homeassistant.helpers.intent": intent_mod,
    "homeassistant.helpers.aiohttp_client": aiohttp_client_mod,
    "homeassistant.helpers.entity_platform": entity_platform_mod,
    "aiohttp": aiohttp_mod,
})
ha.components = components
components.conversation = conversation_mod

sys.path.insert(0, ".")
from custom_components.sysphus_brain import (  # noqa: E402
    SysphusBrainConfig,
    _merged_config,
)
from custom_components.sysphus_brain.const import (  # noqa: E402
    DEFAULT_TIMEOUT,
    DEFAULT_WEBHOOK_URL,
    fallback_speech,
)
from custom_components.sysphus_brain.conversation import (  # noqa: E402
    SysphusBrainAgent,
)


def make_agent() -> SysphusBrainAgent:
    entry = ConfigEntry()
    entry.runtime_data = SysphusBrainConfig(
        webhook_url=DEFAULT_WEBHOOK_URL, timeout=DEFAULT_TIMEOUT
    )
    agent = SysphusBrainAgent(entry)  # type: ignore[arg-type]
    agent.hass = HomeAssistant()
    return agent


def user_input(text: str, language: str = "zh-CN") -> ConversationInput:
    return ConversationInput(text=text, language=language)


def reset() -> None:
    global BUILT_IN_RESULT, BUILT_IN_RAISES, WEBHOOK_REPLY, WEBHOOK_RAISES
    BUILT_IN_RESULT = None
    BUILT_IN_RAISES = False
    WEBHOOK_REPLY = None
    WEBHOOK_RAISES = False
    CALLS["converse_agent_ids"].clear()
    CALLS["webhook_posts"].clear()


async def main() -> None:
    global BUILT_IN_RESULT, BUILT_IN_RAISES, WEBHOOK_REPLY, WEBHOOK_RAISES

    # -- merged config defaults -------------------------------------------
    entry = ConfigEntry()
    cfg = _merged_config(entry)
    assert cfg.webhook_url == DEFAULT_WEBHOOK_URL, cfg
    assert cfg.timeout == DEFAULT_TIMEOUT, cfg
    entry.data = {"webhook_url": "http://example/brain", "timeout": 42}
    entry.options = {"timeout": 7}
    cfg = _merged_config(entry)
    assert cfg.webhook_url == "http://example/brain" and cfg.timeout == 7, cfg
    print("ok: config merge (defaults, data, options override)")

    # -- 1. fast path -------------------------------------------------------
    reset()
    built_in = ConversationResult(
        response=IntentResponse(language="zh-CN"), conversation_id="conv-1"
    )
    built_in.response.async_set_speech("已经关了。")
    BUILT_IN_RESULT = built_in
    agent = make_agent()
    result = await agent._async_handle_message(
        user_input("关掉客厅的灯"), None
    )
    assert result is built_in, "fast path must return the built-in result"
    assert CALLS["converse_agent_ids"] == ["conversation.home_assistant"], CALLS
    assert CALLS["webhook_posts"] == [], "webhook must not be called"
    print("ok: fast path returns built-in result, webhook untouched")

    # -- 2. fallthrough -----------------------------------------------------
    reset()
    err = ConversationResult(
        response=IntentResponse(language="zh-CN"), conversation_id="conv-1"
    )
    err.response.async_set_error(
        IntentResponseErrorCode.NO_INTENT_MATCH, "Sorry, I couldn't understand"
    )
    BUILT_IN_RESULT = err
    WEBHOOK_REPLY = {"response": "好的，电视关了，灯也调暗了。"}
    result = await agent._async_handle_message(
        user_input("把电视关了，灯暗一点"), None
    )
    assert result.response.speech == "好的，电视关了，灯也调暗了。", result
    assert result.response.response_type is IntentResponseType.ACTION_DONE
    assert len(CALLS["webhook_posts"]) == 1, CALLS
    post = CALLS["webhook_posts"][0]
    assert post["url"] == DEFAULT_WEBHOOK_URL, post
    assert post["json"]["text"] == "把电视关了，灯暗一点", post
    assert post["json"]["language"] == "zh-CN", post
    assert post["json"]["satellite_id"] == "assist_satellite.coffee_corner"
    assert post["timeout"] == DEFAULT_TIMEOUT, post
    print("ok: fallthrough posts to webhook and speaks its reply")

    # -- 3a. fallback on webhook timeout (zh) -------------------------------
    reset()
    BUILT_IN_RESULT = err
    WEBHOOK_RAISES = True
    result = await agent._async_handle_message(user_input("讲个笑话"), None)
    assert result.response.speech == fallback_speech("zh-CN"), result
    assert "没反应过来" in result.response.speech
    print("ok: webhook timeout -> Chinese fallback sentence")

    # -- 3b. fallback in English --------------------------------------------
    reset()
    BUILT_IN_RESULT = err
    WEBHOOK_RAISES = True
    result = await agent._async_handle_message(
        user_input("tell me a joke", language="en-US"), None
    )
    assert result.response.speech == fallback_speech("en-US"), result
    print("ok: webhook timeout -> English fallback sentence")

    # -- 3c. built-in delegation itself explodes -> webhook still used -----
    reset()
    BUILT_IN_RAISES = True
    WEBHOOK_REPLY = {"response": "在呢。"}
    result = await agent._async_handle_message(user_input("你好"), None)
    assert result.response.speech == "在呢。", result
    print("ok: built-in exception -> falls through to brain")

    # -- 3d. webhook returns junk -> fallback --------------------------------
    reset()
    BUILT_IN_RESULT = err
    WEBHOOK_REPLY = {"unexpected": True}
    result = await agent._async_handle_message(user_input("你好"), None)
    assert result.response.speech == fallback_speech("zh-CN"), result
    print("ok: malformed webhook reply -> fallback sentence")

    # -- supported languages --------------------------------------------------
    assert make_agent().supported_languages == "*"
    print("ok: supported_languages is '*'")

    print("\nALL OFFLINE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
