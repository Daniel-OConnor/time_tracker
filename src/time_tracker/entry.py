from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entry:
    start_time: datetime
    pauses: bool
    name: str
    level: int
