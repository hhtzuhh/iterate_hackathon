  cd blaxelAgent
  python -m venv .venv && source .venv/bin/activate
  pip install -e .
  cp .env.template .env   # fill in ANTHROPIC_API_KEY
  python run.py           # → http://127.0.0.1:8000