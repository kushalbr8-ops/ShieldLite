// agent/js-agent.js
// Minimal ShieldLite frontend agent.
// Replace SERVER_URL and API_KEY with your values.

(function () {
        const SERVER = "http://YOUR_SERVER_IP:8000/event"; // e.g. http://203.0.113.5:8000/event
        const API_KEY = "PASTE_SHIELD_API_KEY_HERE";
      
        function sendEvent(payload, endpoint) {
          try {
            fetch(SERVER, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-API-KEY": API_KEY
              },
              body: JSON.stringify({
                ip: null,
                payload: payload,
                endpoint: endpoint || window.location.pathname
              })
            }).catch(() => {/* ignore network errors */});
          } catch (e) { /* ignore */ }
        }
      
        // Examples: page-start, form-submit, link click, failed login (if JS can detect)
        sendEvent("page_load: " + location.href, location.pathname);
      
        // attach to form submits
        document.addEventListener("submit", function (e) {
          try {
            const target = e.target;
            const name = target.id || target.name || "form";
            sendEvent("form_submit: " + name + " @ " + location.href, location.pathname);
          } catch (err) {}
        }, true);
      
        // capture suspicious text in inputs (optional)
        document.addEventListener("keypress", function (e) {
          // very light telemetry only; do not capture PII/passwords
          // example: if user types many quotes/backslashes quickly, send a short note
          if (e.key === "'" || e.key === '"' || e.key === ";") {
            sendEvent("suspicious_char_typed: " + e.key, location.pathname);
          }
        }, true);
      
      })();