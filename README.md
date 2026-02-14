# SafeCall

When you're in an accident, the last thing you want to deal with is navigating insurance bureaucracy. **SafeCall** connects you directly to your insurance provider through a single phone call -- we handle the rest.

## How it works

1. **You call SafeCall** after an accident
2. **ElevenLabs voice AI** answers and walks you through the process conversationally
3. **Your insurance details are collected**, a policy document is generated inside a secure **Blaxel sandbox**, and emailed to you on the spot

## Tech stack

- **ElevenLabs** -- Conversational voice AI for the phone call
- **Blaxel Sandboxes** -- Secure, isolated compute environment for PDF generation and email delivery
- **Google ADK + Claude** -- Agent orchestration and reasoning
- **FastAPI + SSE** -- Real-time streaming backend
- **SendGrid** -- Transactional email with PDF attachments

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.template .env   # fill in your keys
python run.py            # → http://127.0.0.1:8000
```

## Environment variables

See `.env.template` for the full list. You'll need:

- `ANTHROPIC_API_KEY` -- Claude API key
- `BL_WORKSPACE` / `BL_API_KEY` -- Blaxel workspace credentials
- `SENDGRID_API_KEY` -- SendGrid API key for email delivery
