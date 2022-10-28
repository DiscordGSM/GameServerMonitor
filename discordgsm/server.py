from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult


@dataclass
class Server:
    id: int
    position: int
    guild_id: int
    channel_id: int
    message_id: Optional[int]
    game_id: str
    address: str
    query_port: str
    query_extra: dict
    status: bool
    result: GamedigResult
    style_id: str
    style_data: dict

    @staticmethod
    def new(guild_id: int, channel_id: int, game_id: str, address: str, query_port: str, query_extra: dict, result: GamedigResult) -> Server:
        return Server(
            id=None,
            position=None,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=None,
            game_id=game_id,
            address=address,
            query_port=query_port,
            query_extra={k: str(v) for k, v in query_extra.items()},
            status=True,
            result=result,
            style_id=None,
            style_data={}
        )

    @staticmethod
    def from_distinct_query(row: tuple) -> Server:
        return Server(
            id=None,
            position=None,
            guild_id=None,
            channel_id=None,
            message_id=None,
            game_id=row[0],
            address=row[1],
            query_port=row[2],
            query_extra=json.loads(row[3]),
            status=row[4] == 1,
            result=json.loads(row[5]),
            style_id=None,
            style_data=None,
        )

    @staticmethod
    def from_list(row: tuple, filter_secret=False) -> Server:
        query_extra: dict = json.loads(row[8])
        style_data: dict = json.loads(row[12])

        if filter_secret:
            query_extra = {k: v for k, v in query_extra.items() if not str(k).startswith('_')}
            style_data = {k: v for k, v in style_data.items() if not str(k).startswith('_')}

        return Server(
            id=row[0],
            position=row[1],
            guild_id=int(row[2]),
            channel_id=int(row[3]),
            message_id=None if row[4] is None else int(row[4]),
            game_id=row[5],
            address=row[6],
            query_port=row[7],
            query_extra=query_extra,
            status=row[9] == 1,
            result=json.loads(row[10]),
            style_id=row[11],
            style_data=style_data,
        )
