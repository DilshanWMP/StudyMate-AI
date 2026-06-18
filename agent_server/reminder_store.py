import os

SCHEDULES_FILE = os.path.join(os.path.dirname(__file__), "..", "schedules.txt")
SCHEDULES_FILE = os.path.abspath(SCHEDULES_FILE)


def save_reminder(description: str, datetime_str: str) -> None:
    """Append a confirmed reminder to schedules.txt in the format:
    [Event Description] | [Date and Time]
    """
    line = f"{description.strip()} | {datetime_str.strip()}\n"
    with open(SCHEDULES_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def read_reminders() -> list[tuple[str, str]]:
    """Read all saved reminders as a list of (description, datetime_str) tuples."""
    if not os.path.exists(SCHEDULES_FILE):
        return []

    reminders = []
    with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            description, datetime_str = line.split("|", 1)
            reminders.append((description.strip(), datetime_str.strip()))
    return reminders