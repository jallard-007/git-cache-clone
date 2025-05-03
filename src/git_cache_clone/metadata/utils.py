import datetime


def get_datetime_now() -> datetime.datetime:
    return datetime.datetime.now().replace(microsecond=0)


def convert_to_utc_iso_string(dt: datetime.datetime) -> str:
    dt_no_tz = dt.astimezone(tz=datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    return dt_no_tz.isoformat() + "Z"


def parse_utc_iso_to_datetime(iso_str: str) -> datetime.datetime:
    """Convert UTC ISO 8601 str to datetime.datetime object."""
    dt = datetime.datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=datetime.timezone.utc)


def parse_utc_iso_to_local_datetime(iso_str: str) -> datetime.datetime:
    """Convert UTC ISO 8601 str to local time datetime.datetime object."""
    dt_utc = parse_utc_iso_to_datetime(iso_str)
    return dt_utc.astimezone().replace(tzinfo=None)
