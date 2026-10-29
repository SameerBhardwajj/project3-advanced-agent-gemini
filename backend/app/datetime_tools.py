from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re

IST = ZoneInfo("Asia/Kolkata")


def get_current_datetime():
    now = datetime.now(IST)

    return {
        "current_datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "timezone": "Asia/Kolkata",
    }


def resolve_datetime(expression: str, timezone: str = "Asia/Kolkata"):
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)

    text = expression.lower().strip()

    # today
    if text == "today":
        result = now

    # tomorrow
    elif text == "tomorrow":
        result = now + timedelta(days=1)

    # yesterday
    elif text == "yesterday":
        result = now - timedelta(days=1)

    # in N days
    else:
        match = re.fullmatch(r"in\s+(\d+)\s+days?", text)

        if match:
            days = int(match.group(1))
            result = now + timedelta(days=days)

        else:
            match = re.fullmatch(r"in\s+(\d+)\s+hours?", text)

            if match:
                hours = int(match.group(1))
                result = now + timedelta(hours=hours)

            else:
                raise ValueError(
                    f"Unsupported date/time expression: {expression}"
                )

    return {
        "relative_expression": expression,
        "resolved_datetime": result.isoformat(),
        "date": result.strftime("%Y-%m-%d"),
        "time": result.strftime("%H:%M:%S"),
        "timezone": timezone,
    }