"""Conversation agent platform for Sysphus Brain."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

import aiohttp

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    HOME_ASSISTANT_AGENT,
    ConversationEntity,
    ConversationEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SysphusBrainConfigEntry
from .const import fallback_speech

if TYPE_CHECKING:
    from homeassistant.components.conversation import (
        ChatLog,
        ConversationInput,
        ConversationResult,
    )

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SysphusBrainConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sysphus Brain conversation agent entity."""
    async_add_entities([SysphusBrainAgent(entry)])


class SysphusBrainAgent(ConversationEntity):
    """Conversation agent: built-in intents first, Sysphus brain second."""

    _attr_name = "Sysphus"
    _attr_supported_features = ConversationEntityFeature.CONTROL
    _attr_supports_streaming = False

    def __init__(self, entry: SysphusBrainConfigEntry) -> None:
        """Initialize the agent."""
        self._entry = entry
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages (all; Sysphus is multilingual)."""
        return "*"

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        """Handle one user utterance.

        Fast path first: delegate to the built-in agent and return its
        result unless it is an error. Fall through to the brain webhook
        otherwise.
        """
        result = await self._async_try_built_in(user_input)
        if result is not None:
            return result

        speech = await self._async_ask_brain(user_input)
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(speech)
        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )

    async def _async_try_built_in(
        self, user_input: ConversationInput
    ) -> ConversationResult | None:
        """Delegate to Home Assistant's built-in conversation agent.

        Returns the built-in agent's result when it handled the text
        (response is not an error); None when the caller should fall
        through to the brain. Delegation always targets the built-in
        agent id explicitly, so this agent can never call itself.
        """
        try:
            result = await conversation.async_converse(
                self.hass,
                text=user_input.text,
                conversation_id=user_input.conversation_id,
                context=user_input.context,
                language=user_input.language,
                agent_id=HOME_ASSISTANT_AGENT,
                device_id=user_input.device_id,
                satellite_id=user_input.satellite_id,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Delegation to the built-in conversation agent failed; "
                "falling through to the brain"
            )
            return None

        if result.response.response_type is intent.IntentResponseType.ERROR:
            _LOGGER.debug(
                "Built-in agent did not handle %r (%s); falling through "
                "to the brain",
                user_input.text,
                result.response.error_code,
            )
            return None
        return result

    async def _async_ask_brain(self, user_input: ConversationInput) -> str:
        """POST the utterance to the brain webhook and await a reply."""
        config = self._entry.runtime_data
        payload: dict[str, Any] = {
            "text": user_input.text,
            "language": user_input.language,
            "conversation_id": user_input.conversation_id,
            "device_id": user_input.device_id,
            "satellite_id": user_input.satellite_id,
        }
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                config.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Brain webhook %s did not answer in time",
                config.webhook_url,
                exc_info=True,
            )
            return fallback_speech(user_input.language)

        text = data.get("response") if isinstance(data, dict) else None
        if not text:
            _LOGGER.warning("Brain webhook returned no response text")
            return fallback_speech(user_input.language)
        return str(text)
