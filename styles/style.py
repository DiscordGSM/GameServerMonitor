from abc import ABC, abstractmethod
from typing import Optional, Union

from discord import Embed, Emoji, PartialEmoji
from discord.ui import TextInput
from server import Server


class Style(ABC):
    """DiscordGSM Message Style Abstract Class"""
    
    def __init__(self, server: Server):
        super().__init__()
        self.server = server
    
    @property
    def id(self) -> str:
        return self.__class__.__name__
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def emoji(self) -> Optional[Union[str, Emoji, PartialEmoji]]:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def default_edit_fields(self) -> dict[str, TextInput]:
        raise NotImplementedError()
    
    @abstractmethod
    def default_style_data(self):
        raise NotImplementedError()
    
    @abstractmethod
    def embed(self) -> Embed:
        raise NotImplementedError()
