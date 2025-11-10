import uuid
from typing import Any
from datetime import datetime


def generate_business_id() -> str:
    return str(uuid.uuid4())

def create_datetime() -> Any:
    return datetime.now()

def get_now_with_milliseconds():
    now = create_datetime()
    return now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond / 1000):03d}"

def get_today():
    now = create_datetime()
    return now.strftime("%Y-%m-%d")
