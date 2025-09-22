from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import DEBUG
from typing import Any, Sequence

from bs4 import BeautifulSoup
from ics import Calendar, Event
from requests import request

debug = False


@dataclass
class Race:
    date: datetime
    name: str
    race_class: str
    winner: str | None

    def __repr__(self) -> str:
        return f"[{self.race_class}] {self.name} ({self.date.date()}) {'' if self.winner is None else f'Winner: {self.winner}'}"


def get_races(url: str) -> list[Race]:
    res = request("GET", url)
    assert res.ok

    tree = BeautifulSoup(res.text, features="lxml")
    assert tree.find("div", class_="page-title").text == "Calendar"

    year = (
        tree.find("select", attrs={"name": "year"})
        .find("option", attrs={"selected": ""})
        .text
    )
    assert year

    table = tree.find("table", class_="basic")

    # assert correct table format
    header: list[Any] = list(table.find_all("th"))
    for r, e in zip(header, ("Date", "Date", "Race", "Winner", "Class")):
        assert r.text == e

    races: list[Race] = []

    for row in table.find_all("tr"):
        data: list[str] = [td.text for td in row.find_all("td")]

        if not data:
            continue

        if "-" in data[0]:
            # multiday race
            start, end = data[0].split(" - ", 1)
            races.append(
                Race(
                    datetime.strptime(f"{start}.{year}", "%d.%m.%Y"),
                    data[2] + " (START)",
                    data[4],
                    data[3] if data[3] else None,
                )
            )
            races.append(
                Race(
                    datetime.strptime(f"{end}.{year}", "%d.%m.%Y"),
                    data[2] + " (END)",
                    data[4],
                    data[3] if data[3] else None,
                )
            )
        else:
            races.append(
                Race(
                    datetime.strptime(f"{data[0]}.{year}", "%d.%m.%Y"),
                    data[2],
                    data[4],
                    data[3] if data[3] else None,
                )
            )

    return races


def create_ics(races: Sequence[Race]) -> Calendar:
    c = Calendar()

    for race in races:
        desc = f"Race: {race.name}\nClass: {race.race_class}"
        if race.winner is not None:
            desc += f"\nWinner: {race.winner}"

        e = Event(name=f"Race: {race.name}", begin=race.date.date(), description=desc)

        e.make_all_day()
        c.events.add(e)

    return c


def write_ics(ics: Calendar, path: str):
    p = Path(path)
    if p.exists():
        prompt = input(f"{p} exists. Overwrite? [Y/n] ")
        if prompt not in ("Y", "y", "yes", "ye", ""):
            raise KeyboardInterrupt

    with open(str(p), "w") as f:
        f.writelines(ics.serialize_iter())


def main(url: str, file: str) -> int | None:
    races = get_races(url)

    print(f"Found {len(races)} races:")
    for i, race in enumerate(races, 1):
        print(f"{i:>3}. {race}")

    prompt = input("Proceed with these races? [Y/n] ")
    if prompt not in ("Y", "y", "yes", "ye", ""):
        return 1

    ics = create_ics(races)
    write_ics(ics, file)


def bootstrap() -> int | None:
    url = input("URL: ")
    file = input("FILE: ")

    try:
        return main(url, file)
    except Exception as e:
        print(f"Error occurred ({type(e).__name__}): {' '.join(map(str, e.args))}")
        if debug:
            raise e
        else:
            return 1


if __name__ == "__main__":
    exit(bootstrap())
