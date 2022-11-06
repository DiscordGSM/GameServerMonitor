import os
from abc import ABC, abstractmethod


class Protocol(ABC):
    def __init__(self, address: str, query_port: int):
        self.address = address
        self.query_port = query_port
        self.timeout = float(os.getenv('TASK_QUERY_SERVER_TIMEOUT', '15'))

    @abstractmethod
    async def query():
        raise NotImplementedError()
