"""Constants for the Sysphus Brain integration."""

DOMAIN = "sysphus_brain"

CONF_WEBHOOK_URL = "webhook_url"
CONF_TIMEOUT = "timeout"

DEFAULT_WEBHOOK_URL = "http://192.168.1.91:18793/brain"
DEFAULT_TIMEOUT = 115
MIN_TIMEOUT = 5
MAX_TIMEOUT = 300

_FALLBACK_ZH = "我这会儿没反应过来，再说一次试试。"
_FALLBACK_EN = "Sorry, I didn't catch that. Please say it again."


def fallback_speech(language: str | None) -> str:
    """Return the canned fallback sentence in the conversation's language."""
    if language and language.lower().startswith("en"):
        return _FALLBACK_EN
    return _FALLBACK_ZH
