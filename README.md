# Sysphus Brain

A Home Assistant conversation agent with two stages:

1. **Fast path** — every utterance is first delegated to Home Assistant's
   built-in conversation agent (`conversation.home_assistant`). Precise
   commands ("turn off the living room light") execute instantly, with no
   external involvement, and the built-in agent's result is returned
   unchanged.
2. **Fallthrough** — anything the built-in agent answers with an error
   (typically *no intent match*) is POSTed as JSON to a **brain webhook**
   on the local network. The webhook's reply text is spoken back through
   the Assist pipeline. This is where an external assistant (Sysphus)
   interprets free-form requests — no exact device names or phrasing
   required.

On webhook timeout, HTTP error, or a malformed reply, the agent speaks a
short fallback sentence in the conversation's language.

## Webhook contract

Request (`POST`, JSON):

```json
{
  "text": "把客厅的灯调暗一点，顺便看看猫砂盆今天用了几次",
  "language": "zh-CN",
  "conversation_id": "01J…",
  "device_id": "…",
  "satellite_id": "…"
}
```

Response (JSON, within the configured timeout):

```json
{"response": "灯调暗了。嘻嘻今天去了四次，Fern 两次。"}
```

The reference receiver is a small stdlib-only Python server
(`brain_receiver.py`, part of the author's voice-satellite setup) that
queues requests for an agent runtime and returns whatever reply it
produces.

## Installation

Via [HACS](https://hacs.xyz/) as a custom repository:

1. HACS → Integrations → ⋮ → Custom repositories →
   `https://github.com/CharlesDaiii/hass-sysphus-brain`, category
   *Integration*.
2. Download **Sysphus Brain**, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **Sysphus Brain**.
   Defaults point at the author's LAN receiver
   (`http://192.168.1.91:18793/brain`, 115 s timeout) — adjust to your
   own receiver.
4. Settings → Voice assistants → your pipeline → set the conversation
   agent to **Sysphus**.

Webhook URL and timeout can later be changed under the integration's
*Configure* (options) dialog without recreating the entry.

## License

MIT
