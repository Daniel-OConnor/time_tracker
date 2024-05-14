from datetime import UTC, timedelta, datetime
from pathlib import Path
import sqlite3
import sys
import tzlocal
from typing import Any, Never
from zoneinfo import ZoneInfo

from time_tracker.editor import edit_string_in_vim
from time_tracker.entry import Entry
from time_tracker.parser import format_entries, parse_entries

conn: sqlite3.Connection


def get_cursor() -> "CursorContextManager":
    return CursorContextManager(conn)


class CursorContextManager:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.cursor: sqlite3.Cursor

    def __enter__(self) -> sqlite3.Cursor:
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if exc_type is None:
            self.connection.commit()
        self.cursor.close()


LOCAL = tzlocal.get_localzone()


def error_with(msg: str) -> Never:
    print(msg)
    exit(1)


def to_entry(row: Any) -> Entry:
    entry = Entry(*row)
    entry.pauses = bool(entry.pauses)
    entry.start_time = datetime.fromisoformat(str(entry.start_time))
    return entry


def init() -> None:
    global conn
    (Path.home() / ".tracker").mkdir(exist_ok=True)
    conn = sqlite3.connect((Path.home() / ".tracker/tracker_db"))
    with get_cursor() as cursor:
        cursor = conn.cursor()

        cursor.execute(
            """CREATE TABLE IF NOT EXISTS time_tracker (
                    start_time TIMESTAMP,
                    pauses INTEGER CHECK (pauses IN (0,1)), -- 0 for false, 1 for true
                    name TEXT,
                    level INTEGER
            )"""
        )


def get_records() -> list[Entry]:
    return get_records_day(datetime.now(LOCAL))


def get_records_day(day: datetime) -> list[Entry]:
    query = """SELECT * FROM time_tracker
                WHERE start_time >= ? AND start_time < ?
                ORDER BY start_time DESC"""
    with get_cursor() as cursor:
        day = day.astimezone(LOCAL)
        start_of_day = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        cursor.execute(
            query, (start_of_day.astimezone(UTC), end_of_day.astimezone(UTC))
        )
        return [to_entry(values) for values in cursor.fetchall()]


def last_record() -> Entry | None:
    inactive_levels: int = 100000
    entries = get_records()
    for entry in entries:
        if entry.name == "END":
            inactive_levels = min(inactive_levels, entry.level)
        elif entry.level < inactive_levels:
            return entry
    return None


def insert_cursor(cursor: sqlite3.Cursor, entry: Entry) -> None:
    cursor.execute(
        "INSERT INTO time_tracker (start_time, pauses, name, level) VALUES (?, ?, ?, ?)",
        (entry.start_time, entry.pauses, entry.name, entry.level),
    )


def insert_entry(entry: Entry) -> None:
    entry.start_time = entry.start_time.astimezone(UTC)
    with get_cursor() as cursor:
        insert_cursor(cursor, entry)


def overwrite_date(datetime: datetime, entries: list[Entry]) -> None:
    with get_cursor() as cursor:
        query = """DELETE FROM time_tracker
                WHERE start_time >= ? AND start_time < ?"""
        day = datetime.astimezone(LOCAL)
        start_of_day = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        cursor.execute(
            query, (start_of_day.astimezone(UTC), end_of_day.astimezone(UTC))
        )
        for entry in entries:
            insert_cursor(cursor, entry)


def clean_date(datetime: datetime) -> None:
    pass


def parse_time(arg: str) -> datetime:
    if arg.lower() == "now":
        return datetime.now(tz=UTC)
    elif arg[0] == "-":
        try:
            result: int = int(arg[1:])
        except ValueError:
            error_with(f"{arg[1:]} in {arg[1]} is not an integer")
        delta = timedelta(minutes=result)
        return datetime.now(tz=UTC) - delta
    else:
        if arg.count(":") != 1:
            error_with(f"{arg} is neither -minutes or hour:minutes")
        hour_s, minutes_s = arg.split(":")
        hour, minutes = int(hour_s), int(minutes_s)
        current_time = datetime.now(LOCAL)
        time_local = current_time.replace(
            hour=hour, minute=minutes, second=0, microsecond=0
        )
        time_utc = time_local.astimezone(ZoneInfo("UTC"))
        return time_utc


def start(blocks: bool, next: bool, args: list[str]) -> None:
    if len(args) == 0:
        error_with("track start requires a time and name")
    if args[0][0].isalpha():
        start_time = datetime.now(LOCAL).astimezone(UTC)
        name = " ".join(args)
    else:
        start_time = parse_time(args[0])
        name = " ".join(args[1:])
    if "%" in name:
        error_with("% is a reserved symbol, not permitted in name")
    last = last_record()
    if last is None:
        level = 0
    else:
        level = last.level + (0 if next else 1)
    entry = Entry(start_time=start_time, pauses=blocks, name=name, level=level)
    if next and last is not None:
        print(
            f"ending '{last.name}, start time={last.start_time.astimezone(LOCAL).strftime('%H:%M')}, end_time={entry.start_time.astimezone(LOCAL).strftime('%H:%M')}"
        )
    elif last is not None:
        verb = "pausing" if blocks else "subtask of"
        print(
            f"{verb} '{last.name}, start time={last.start_time.astimezone(LOCAL).strftime('%H:%M')}"
        )
    print(
        f"starting '{name}, start time={entry.start_time.astimezone(LOCAL).strftime('%H:%M')}"
    )
    insert_entry(entry)


def stop(args: list[str]) -> None:
    if len(args) > 1:
        error_with("track end requires only a time")
    start_time = parse_time(args[0]) if len(args) == 1 else datetime.now(tz=UTC)
    last = last_record()
    if last is None:
        level = 0
    else:
        level = last.level
    entry = Entry(start_time=start_time, pauses=False, name="END", level=level)
    if last is None:
        print(f"end time = {entry.start_time.astimezone(LOCAL).strftime('%H:%M')}")
    else:
        print(
            f"ending '{last.name}', start time = {last.start_time.astimezone(LOCAL).strftime('%H:%M')}, end time = {entry.start_time.astimezone(LOCAL).strftime('%H:%M')}"
        )
    insert_entry(entry)
    last = last_record()
    if last is not None:
        print(
            f"returning to '{last.name}', start time = {last.start_time.astimezone(LOCAL).strftime('%H:%M')}"
        )


def date_arg(function_name: str) -> datetime:
    if len(sys.argv) == 3:
        date_string = sys.argv[2]
        date: datetime | None = None
        for time_format in ("%Y-%m-%d", "%Y%m%d", "%m-%d", "%m%d"):
            try:
                date = datetime.strptime(date_string, time_format)
                break
            except ValueError:
                pass
        if date is None:
            error_with(f"{date_string} is not a date")
        if date.year == 1900:
            date = date.replace(year=datetime.now(tz=LOCAL).year).astimezone(LOCAL)
    elif len(sys.argv) == 2:
        date = datetime.now(tz=UTC)
    else:
        error_with(f"{function_name} takes a date, defaults to today")
    return date.astimezone(LOCAL)


def print_date() -> None:
    date = date_arg("print")
    print(format_entries(get_records_day(date), date))


def edit_date() -> None:
    date = date_arg("print")
    text = format_entries(get_records_day(date), date)
    result = edit_string_in_vim(text)
    entries = parse_entries(result)
    overwrite_date(date, entries)


def main() -> None:
    if len(sys.argv) < 2:
        error_with("Error: no arguments")
    init()
    with conn:
        command = sys.argv[1]
        if command == "start":
            if len(sys.argv) >= 2 and sys.argv[2] == "block":
                start(blocks=True, next=False, args=sys.argv[3:])
            else:
                start(blocks=False, next=False, args=sys.argv[2:])
        elif command == "next":
            start(blocks=False, next=True, args=sys.argv[2:])
        elif command == "stop":
            stop(args=sys.argv[2:])
        elif command == "print":
            print_date()
        elif command == "edit":
            edit_date()
        else:
            print(f"Unrecognised command {command}")
