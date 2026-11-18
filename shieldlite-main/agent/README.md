# ShieldLite /agent Readme

This folder contains multiple agent options for customers to integrate with ShieldLite:

1. js-agent.js - quick JS snippet to paste before </body>
2. nginx-snippet.txt - NGINX config for forwarding access_log to your collector
3. syslog-listener.py - UDP syslog listener that parses nginx logs and forwards to /event
4. wp-shieldlite plugin - WordPress plugin that sends pageviews and failed logins
5. install_service.sh - helper to run the syslog listener locally
6. example_test.sh - test curl to the backend

## Quick setup for the syslog listener (recommended for server-level logs)
- Place `syslog-listener.py` on your collector machine (the machine that runs ShieldLite backend or a separate log collector).
- Create and activate venv and install `requests`.
- Run the listener:
  python syslog-listener.py --bind 0.0.0.0 --port 5514 --backend http://127.0.0.1:8000/event --api-key YOUR_SHIELD_API_KEY

- On SME nginx, add the snippet from nginx-snippet.txt and replace YOUR_COLLECTOR_IP with the public IP of your listener.

## Quick setup for browser JS integration (easy, low coverage)
- Paste `js-agent.js` before </body> on customer's site.
- Replace SERVER and API_KEY placeholders.
- Good for lightweight telemetry (page loads, form submits).

## WordPress
- Install plugin `shieldlite-wp` into WordPress.
- Edit the PHP file to set endpoint and API key (or request a plugin config UI later).

## Security notes
- Keep SHIELD API key secret.
- Prefer Cloudflare or origin-level integration for blocking; the JS agent is supplemental only.
- Do not collect PII or passwords.

If you want, I will:
- Create `launchd` plist for macOS or `systemd` unit for Linux to run the syslog listener as a service.
- Create a small admin web page to add/remove blocked IPs manually from the dashboard.
- Turn the WP plugin into a settings-enabled plugin so customers can paste API tokens from their WordPress admin.

Tell me which of those you want next and I’ll produce the files immediately.