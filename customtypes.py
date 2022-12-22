from typing import TypedDict


class MusescoreSongInfo(TypedDict):
    title: str
    link: str
    kind: str
    instrument: str
    votes: int


class SpotifySongInfo(TypedDict):
    title: str
    artist: str


class SongSearch(TypedDict):
    title: str
    artist: str
    kind: str
    instrument: str
