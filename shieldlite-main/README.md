# ShieldLite

ShieldLite is a web-attack monitoring prototype that analyzes incoming events using signature-based, behavioural, and anomaly detection. It can apply local Redis blocks and optionally integrate with Cloudflare when credentials are configured.

## Project structure

- `backend/` — FastAPI event ingestion, detection pipeline, Redis-based counters/blocks, and SQLite attack logging.
- `dashboard/` — Streamlit dashboard for reviewing attack events and blocked IPs.
- `agent/` — Optional JavaScript, NGINX/syslog, and WordPress event-forwarding integrations.

## Requirements

- Python 3.10+
- Redis
- Optional: Cloudflare account/API token and zone ID for Cloudflare blocking

## Setup

1. Create and activate a virtual environment.
2. Install backend dependencies:

   ```bash
   python -m pip install -r backend/requirements.txt
   ```

3. Copy `backend/.env.example` to `backend/.env` and set strong local secrets. **Do not commit `backend/.env`.**
4. Start Redis.
5. Start the API from the `backend` directory:

   ```bash
   cd backend
   uvicorn main:app --reload
   ```

6. In a second terminal, install dashboard dependencies and start the dashboard:

   ```bash
   python -m pip install -r dashboard/requirements.txt
   streamlit run dashboard/dashboard.py
   ```

   Set `DASH_PASS`, `SHIELD_API_KEY`, and `SHIELD_BACKEND_URL` in your local `backend/.env` before using the dashboard.

## Security notes

- Keep `.env`, database files, logs, and real API keys out of Git.
- Rotate any credentials that were ever committed or shared.
- Use HTTPS and a strong API key/password outside local development.
- Treat IP addresses and request payloads in logs as potentially sensitive data.
- The included integrations are prototypes; review data collection and deployment settings before production use.

## License

Add a license before redistributing this project.
