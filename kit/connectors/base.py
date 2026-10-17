"""The shape every connector follows.

A connector lists its objects. Each object says which table it fills, its
columns, and whether it's a snapshot (mirror the source: upsert and prune) or
a history log (only ever add rows).
"""
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass
class ObjectSpec:
    name: str                      # e.g. "crm.opportunities"
    table: str                     # destination table
    columns: list[str]             # destination columns, excluding synced_at
    fetch: Callable[[], Iterable[dict]]  # returns rows keyed by destination column
    mode: str = "snapshot"         # "snapshot" or "history"
    key: str = "id"


class Connector:
    source = "unknown"

    def __init__(self, options: dict):
        self.options = options

    def objects(self) -> list[ObjectSpec]:
        raise NotImplementedError
