"""Shared helpers for demo generators: seeded randomness, business days, seasons, names."""
import datetime as dt
import math
import random

FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Drew", "Quinn", "Reese", "Cameron", "Dana",
         "Parker", "Rowan", "Sydney", "Blake", "Hayden", "Emerson", "Kendall", "Logan", "Peyton", "Skyler", "Marlowe", "Jesse",
         "Ari", "Sam", "Robin", "Frankie", "Charlie", "Elliot", "Harper", "Kai", "Noel", "Shay", "Tatum"]
LAST = ["Alvarez", "Brooks", "Castillo", "Dawson", "Ellison", "Fuentes", "Garner", "Holloway", "Ibarra", "Jennings", "Keller",
        "Lockhart", "Medina", "Nolan", "Ortega", "Pruitt", "Quintero", "Ramsey", "Salinas", "Thornton", "Underwood", "Villarreal",
        "Whitaker", "Yates", "Barrera", "Cobb", "Delgado", "Esparza", "Fowler", "Guerra", "Hendricks", "Lowry", "Mercado",
        "Navarro", "Pace", "Rios", "Stroud", "Tamez", "Vance", "Wade"]


class Rand:
    """Seeded randomness: the same seed and the same parts always give the same numbers."""

    def __init__(self, seed):
        self.seed = seed

    def __call__(self, *parts) -> random.Random:
        return random.Random("|".join(str(p) for p in (self.seed,) + parts))


def business_days(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def mondays(start: dt.date, end: dt.date):
    d = start - dt.timedelta(days=start.weekday())
    while d <= end:
        yield d
        d += dt.timedelta(days=7)


def month_starts(start: dt.date, end: dt.date):
    d = start.replace(day=1)
    while d <= end:
        yield d
        d = (d + dt.timedelta(days=32)).replace(day=1)


def season(day: dt.date, amplitude=0.18, peak_day=150) -> float:
    """1.0 on average; up to 1 + amplitude around `peak_day` of the year (150 = early June)."""
    return 1.0 + amplitude * math.cos((day.timetuple().tm_yday - peak_day) / 365 * 2 * math.pi)


def growth(day: dt.date, start: dt.date, per_year=0.08) -> float:
    return 1.0 + per_year * ((day - start).days / 365)


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    k, p, target = 0, 1.0, math.exp(-lam)
    while True:
        p *= rng.random()
        if p <= target:
            return k
        k += 1


def stamp(day: dt.date, rng: random.Random, start_hour=8, hours=10) -> str:
    """A UTC timestamp during Central business hours on `day` (Central taken as UTC-5)."""
    t = dt.datetime.combine(day, dt.time(start_hour + 5, 0)) + dt.timedelta(minutes=rng.randint(0, hours * 60))
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc(t: dt.datetime) -> str:
    return (t + dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")


def pick_name(rng: random.Random, used: set) -> str:
    for _ in range(50):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name not in used:
            used.add(name)
            return name
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def money_round(v: float) -> float:
    return round(v, -1 if v < 10_000 else -2)
