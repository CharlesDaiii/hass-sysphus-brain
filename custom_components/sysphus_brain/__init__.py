"""The Sysphus Brain integration.

Provides a conversation agent for Assist pipelines with two stages:

1. Fast path - the text is first handed to Home Assistant's built-in
   conversation agent. Precise commands ("turn off the TV") execute
   instantly and their result is returned unchanged.
2. Fallthrough - anything the built-in agent answers with an error
   (typically "no intent match") is POSTed to the Sysphus brain webhook
   on the LAN, and the reply text is spoken back.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_TIMEOUT,
    CONF_WEBHOOK_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_WEBHOOK_URL,
)

PLATFORMS = [Platform.CONVERSATION]


@dataclass
class SysphusBrainConfig:
    """Runtime configuration for a Sysphus Brain config entry."""

    webhook_url: str
    timeout: int


type SysphusBrainConfigEntry = ConfigEntry[SysphusBrainConfig]


def _merged_config(entry: ConfigEntry) -> SysphusBrainConfig:
    """Merge config-entry data with options (options win)."""
    merged = {**entry.data, **entry.options}
    return SysphusBrainConfig(
        webhook_url=merged.get(CONF_WEBHOOK_URL, DEFAULT_WEBHOOK_URL),
        timeout=int(merged.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: SysphusBrainConfigEntry
) -> bool:
    """Set up Sysphus Brain from a config entry."""
    entry.runtime_data = _merged_config(entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(
    hass: HomeAssistant, entry: SysphusBrainConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SysphusBrainConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
