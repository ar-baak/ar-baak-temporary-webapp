from datetime import datetime
import pytz

GMT8 = pytz.timezone("Asia/Hong_Kong")


def get_today_gmt8_str() -> str:
    """Returns the current date in GMT+8 timezone as a string."""
    return (datetime.now(GMT8)).strftime("%Y-%m-%d")


def get_today_gmt8() -> datetime:
    """Returns the current date in GMT+8 timezone as a string."""
    return datetime.now(GMT8)
