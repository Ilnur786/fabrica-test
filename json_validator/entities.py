from dataclasses import dataclass
from datetime import datetime


@dataclass
class Distribution:
    id: int
    distr_start_date: datetime
    distr_text: str
    client_filter: str
    distr_end_date: datetime


@dataclass
class Client:
    id: int
    mobile_number: str
    mobile_operator_code: str
    tag: str
    # timezone field should be chosen between:
    # datetime.timezone or datetime.datetime.now(tz=pytz.timezone(tzlocal.get_localzone_name()))
    # second one is equal to datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))
    timezone: str  # or str if it will be looks like 'Europe/Moscow'


@dataclass
class Message:
    id: int
    send_date: datetime
    status: bool
    dist_id: int
    client_id: int
