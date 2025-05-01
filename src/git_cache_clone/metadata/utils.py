import datetime


def get_utc_naive_datetime_now() -> datetime.datetime:
    return convert_to_utc_naive_datetime(datetime.datetime.now())


def convert_to_utc_naive_datetime(dt: datetime.datetime) -> datetime.datetime:
    return dt.astimezone(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def convert_to_utc_iso_string(dt: datetime.datetime) -> str:
    dt_utc = convert_to_utc_naive_datetime(dt)
    return dt_utc.isoformat() + "Z"


def parse_utc_iso_to_datetime(iso_str: str) -> datetime.datetime:
    """Convert UTC ISO 8601 str to datetime.datetime object."""
    dt_naive = datetime.datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt_naive.replace(tzinfo=datetime.timezone.utc)


def parse_utc_iso_to_local_datetime(iso_str: str) -> datetime.datetime:
    """Convert UTC ISO 8601 str to local time datetime.datetime object."""
    dt_utc = parse_utc_iso_to_datetime(iso_str)
    return dt_utc.astimezone().replace(tzinfo=None)
