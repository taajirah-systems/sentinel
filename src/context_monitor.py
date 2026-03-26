import asyncio
import json
import logging
import subprocess
import time
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ContextMonitor: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()

# CLI Path
OPENCLAW_CLI = "/opt/homebrew/bin/openclaw"

# Alert thresholds
ALERT_THRESHOLD_PERCENT = 90
CRITICAL_THRESHOLD_PERCENT = 98

# Debounce alerts to avoid spamming (seconds)
ALERT_COOLDOWN = 60
last_alert_time = 0

def send_notification(title, message, sound="Basso"):
    """Sends a macOS system notification."""
    try:
        script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
        subprocess.run(["osascript", "-e", script], check=True)
        logging.info(f"Notification sent: {title} - {message}")
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")

async def monitor():
    global last_alert_time
    logging.info(f"Starting Context Monitor using CLI: {OPENCLAW_CLI}")
    
    while True:
        try:
            # Run openclaw sessions --json
            result = subprocess.run(
                [OPENCLAW_CLI, "sessions", "--json"],
                capture_output=True,
                text=True,
                check=False 
            )

            if result.returncode != 0:
                logging.error(f"CLI Error: {result.stderr.strip()}")
                await asyncio.sleep(10)
                continue

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                logging.error("Failed to parse JSON output from CLI.")
                await asyncio.sleep(10)
                continue

            sessions = []
            defaults = {}
            if isinstance(data, list):
                sessions = data
            elif isinstance(data, dict):
                payload = data.get("payload", {})
                sessions = payload.get("sessions", []) if isinstance(payload, dict) else []
                defaults = payload.get("defaults", {}) if isinstance(payload, dict) else {}
                if not sessions:
                     sessions = data.get("sessions", [])

            if sessions:
                for session in sessions:
                    total_tokens = session.get("totalTokens") or 0
                    context_limit = session.get("contextTokens") or defaults.get("contextTokens") or 1048576 
                    
                    if context_limit > 0:
                        usage_percent = (total_tokens / context_limit) * 100
                        
                        if usage_percent > 10:
                            logging.debug(f"Session {session.get('sessionId', 'unknown')}: {usage_percent:.2f}% ({total_tokens}/{context_limit})")
                        
                        current_time = time.time()
                        if usage_percent >= ALERT_THRESHOLD_PERCENT:
                            if (current_time - last_alert_time) > ALERT_COOLDOWN:
                                if usage_percent >= CRITICAL_THRESHOLD_PERCENT:
                                    send_notification(
                                        "⚠️ CRITICAL: Context Full", 
                                        f"Agent is at {usage_percent:.1f}% capacity! RESTART SOON.",
                                        "Sosumi"
                                    )
                                else:
                                    send_notification(
                                        "Context Warning",
                                        f"Agent context usage is high: {usage_percent:.1f}%",
                                        "Ping"
                                    )
                                last_alert_time = current_time
                                break # One notification per cycle is enough
            
            # Wait before polling again
            await asyncio.sleep(10) 

        except Exception as e:
             logging.error(f"Unexpected monitor error: {e}. Retrying in 10s...")
             await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        logging.info("Stopping Context Monitor.")
