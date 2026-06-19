import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agent_server"))

from datetime import datetime
from temporalio import activity
import requests

from reminder_store import read_reminders, remove_reminder

AGENT_SERVER_URL = "http://localhost:8000"


def parse_datetime(dt_str: str) -> datetime | None:
    """Try to parse the stored datetime string into a real datetime object.
    Returns None if it can't be parsed (e.g. vague text like 'tomorrow at 6pm')."""
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue
    return None


@activity.defn
async def check_and_trigger_reminders() -> int:
    """Reads schedules.txt, finds reminders whose time has passed,
    sends them to the Agent Server's /trigger endpoint, and removes
    them from the file. Returns the number of reminders triggered."""
    reminders = read_reminders()
    now = datetime.now()
    triggered_count = 0

    for description, datetime_str in reminders:
        scheduled_time = parse_datetime(datetime_str)

        if scheduled_time is None:
            # Can't parse it — skip rather than crash or silently drop it
            activity.logger.warning(
                f"Could not parse datetime '{datetime_str}' for reminder '{description}', skipping."
            )
            continue

        if scheduled_time <= now:
            try:
                response = requests.post(
                    f"{AGENT_SERVER_URL}/trigger",
                    json={"description": description, "datetime": datetime_str},
                    timeout=10,
                )
                response.raise_for_status()
                remove_reminder(description, datetime_str)
                triggered_count += 1
            except requests.exceptions.RequestException as e:
                activity.logger.error(f"Failed to trigger reminder '{description}': {e}")
                # Don't remove it — let Temporal retry this activity later
                raise

    return triggered_count