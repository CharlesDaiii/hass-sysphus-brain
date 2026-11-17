"""Config flow for the Sysphus Brain integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_TIMEOUT,
    CONF_WEBHOOK_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_WEBHOOK_URL,
    DOMAIN,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the settings form schema with the given defaults."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_WEBHOOK_URL,
                default=defaults.get(CONF_WEBHOOK_URL, DEFAULT_WEBHOOK_URL),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            vol.Optional(
                CONF_TIMEOUT,
                default=int(defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_TIMEOUT,
                    max=MAX_TIMEOUT,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize submitted form values for storage."""
    return {
        CONF_WEBHOOK_URL: str(
            user_input.get(CONF_WEBHOOK_URL, DEFAULT_WEBHOOK_URL)
        ).strip(),
        CONF_TIMEOUT: int(user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
    }


class SysphusBrainConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sysphus Brain."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial (and only) setup step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Sysphus Brain", data=_normalize(user_input)
            )
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return SysphusBrainOptionsFlow()


class SysphusBrainOptionsFlow(OptionsFlow):
    """Handle Sysphus Brain options (webhook URL and timeout)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=_normalize(user_input))
        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults))
