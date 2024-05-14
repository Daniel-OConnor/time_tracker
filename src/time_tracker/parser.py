from datetime import UTC, datetime, timedelta
from time_tracker.entry import Entry
import tzlocal

LOCAL = tzlocal.get_localzone()


def format_entries(entries: list[Entry], date: datetime) -> str:
    text = ""
    entries = sorted(entries, key=lambda x: x.start_time)
    text += date.strftime("%Y-%m-%d") + "\n\n"
    if len(entries) == 0:
        return text
    for entry in entries:
        if entry.start_time.astimezone(LOCAL).date() != date.astimezone(LOCAL).date():
            raise RuntimeError(
                f"can only create entries file for entries in the same day, times {entry.start_time} and {date}, {entry.start_time.astimezone(LOCAL).date()} {date.astimezone(LOCAL).date()}"
            )
        text += (
            "\t" * entry.level
            + entry.start_time.astimezone(LOCAL).strftime("%H:%M")
            + "  "
            + entry.name
            + (" %pauses" if entry.pauses else "")
            + "\n"
        )
    return text


def parse_entries(text: str) -> list[Entry]:
    entries: list[Entry] = []
    lines = list(text.split("\n"))
    if len(lines[1]) != 0:
        raise RuntimeError("Second line must be empty")

    today = datetime.strptime(lines[0], "%Y-%m-%d").astimezone(LOCAL)
    for line in lines[2:]:
        if len(line) == 0:
            continue
        level: int
        for i, char in enumerate(line):
            if char != "\t":
                level = i
                break
        line = line[level:]
        hours = line[:2]
        assert line[2] == ":"
        minutes = line[3:5]
        start_time = (
            today + timedelta(hours=int(hours), minutes=int(minutes))
        ).astimezone(UTC)
        line = line[5:].strip()
        pauses = " %pauses" in line
        if pauses:
            name = line.split(" %pauses")[0]
        else:
            name = line
        entries.append(
            Entry(start_time=start_time, pauses=pauses, name=name, level=level)
        )

    return entries
