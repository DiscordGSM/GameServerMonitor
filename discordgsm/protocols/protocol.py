import os
from abc import ABC, abstractmethod


class Protocol(ABC):
    pre_query_required = False

    def __init__(self, kv: dict):
        self.kv = kv
        self.timeout = float(os.getenv('TASK_QUERY_SERVER_TIMEOUT', '15'))

    async def pre_query(self):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def query(self):
        raise NotImplementedError()
