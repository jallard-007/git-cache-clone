import datetime


def get_utc_naive_datetime_now() -> datetime.datetime:
    return convert_to_utc_naive_datetime(datetime.datetime.now())


def convert_to_utc_naive_datetime(dt: datetime.datetime) -> datetime.datetime:
    return dt.astimezone(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def parse_utc_naive_iso_to_local_datetime(iso_str: str) -> datetime.datetime:
    """Convert UTC naive ISO 8601 str to local time datetime.datetime object."""
    dt_naive = datetime.datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S")
    dt_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
    return dt_utc.astimezone().replace(tzinfo=None)
