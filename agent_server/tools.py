from langchain_core.tools import tool
from reminder_store import save_reminder


@tool
def create_schedule(description: str, datetime: str) -> str:
    """Creates a reminder schedule for the user.

    Use this tool only when the user explicitly asks to be reminded
    about something at a specific date and/or time. Do not use this
    tool for casual conversation or general questions.

    Args:
        description: A short description of what the reminder is for,
            e.g. "Study DSP" or "Submit assignment".
        datetime: The exact date and time the reminder should fire,
            STRICTLY in the format "YYYY-MM-DD HH:MM" (24-hour time),
            e.g. "2026-06-20 18:00". Always resolve relative terms like
            "tomorrow" or "in 10 minutes" into this exact format yourself
            based on the current date and time before calling this tool.
    """
    save_reminder(description, datetime)
    return f"Schedule created: {description} at {datetime}"