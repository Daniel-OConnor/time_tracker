from datetime import UTC, timedelta, datetime
from pathlib import Path
import sqlite3
import sys
import tzlocal
import time
from typing import Never
from zoneinfo import ZoneInfo

conn: sqlite3.Connection

def error_with(msg: str) -> Never:
    print(msg)
    exit(1)

def init():
    global conn
    conn = sqlite3.connect((Path.home() / '.tracker/tracker_db'))
    (Path.home() / '.tracker').mkdir(exist_ok=True)
    with sqlite3.connect('your_database.db') as conn:
        cursor = conn.cursor()

        # Create table if not exists with constraint
        cursor.execute('''CREATE TABLE IF NOT EXISTS your_table (
                            start_time TIMESTAMP,
                            interrupts INTEGER CHECK (interrupts IN (0,1)), -- 0 for false, 1 for true
                            name TEXT,
                            level INTEGER
                        )''')
        
def parse_time(arg: str) -> datetime:
    if arg[0] == '-':
        try:
            result: int = int(arg[1:])
        except ValueError:
            error_with(f'{arg[1:]} in {arg[1]} is not an integer')
        delta = timedelta(minutes=result)
        return datetime.now(tz = UTC) - delta
    else:
        if arg.count(':') != 1:
            error_with(f"{arg} is neither -minutes or hour:minutes")
        hour, minutes = arg.split(':')
        hour, minutes = int(hour), int(minutes)
        current_time = datetime.now(tzlocal.get_localzone())
        time_local = current_time.replace(hour=hour, minute=minutes, second=0, microsecond=0)
        time_utc = time_local.astimezone(ZoneInfo('UTC'))
        return time_utc


def start(blocks: bool, args: list[str]):
    if len(args) < 2:
        error_with("track start requires a time and name")
    start_time = parse_time(args[0])
    


def end():
    pass


def main():
    if len(sys.argv) < 2:
        error_with("Error: no arguments")

    command = sys.argv[1]
    if command == "start":
        if len(sys.argv) >= 2 and sys.argv[2] == "block":
            start(blocks=True, args=sys.argv[3:])
        else:
            start(blocks=False, args=sys.argv[2:])
    elif command == "end":
        end()
    else:
        print(f"Unrecognised command {command}")
