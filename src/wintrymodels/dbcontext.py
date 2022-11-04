import abc
from logging import Logger
from typing import ClassVar, Optional, Protocol, Type

from sqlmodel.ext.asyncio.session import AsyncSession, AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine


# This has to serve as an abstraction over the concept of a session
# that many ORM handles, so we can provide a UoW and Repository unified
# experience
from wintry import App, inject


class DataContext(abc.ABC):
    @abc.abstractmethod
    async def commit(self) -> None:
        """
        Flushes current state to DB

        Returns:

        """
        pass

    @abc.abstractmethod
    async def rollback(self) -> None:
        """Rollback current state"""
        pass

    @abc.abstractmethod
    def begin(self, **kw) -> None:
        """Start a new transaction"""
        pass

    @abc.abstractmethod
    async def dispose(self):
        """Release resources"""
        pass


class SyncDataContext(abc.ABC):
    @abc.abstractmethod
    def commit(self) -> None:
        """
        Flushes current state to DB

        Returns:

        """
        pass

    @abc.abstractmethod
    def rollback(self) -> None:
        """Rollback current state"""
        pass

    @abc.abstractmethod
    def begin(self) -> None:
        """Start a new transaction"""
        pass

    @abc.abstractmethod
    def dispose(self):
        """Release resources"""
        pass


class SQLEngineContextNotInitializedException(Exception):
    pass


class EngineContextProtocol(Protocol):
    @classmethod
    def config(cls, url: str, echo: bool = True):
        pass

    @classmethod
    def get_client(cls):
        pass


class AsyncSQLEngineContext(EngineContextProtocol):
    _client: ClassVar[Optional[AsyncEngine]] = None

    @classmethod
    def config(cls, url: str, echo: bool = True):
        if cls._client is None:
            cls._client = create_async_engine(url, echo=echo)

    @classmethod
    def get_client(cls):
        if cls._client is None:
            raise SQLEngineContextNotInitializedException()
        return cls._client


def add_data_context(app: App, engine: Type[EngineContextProtocol], url: str):
    @app.on_startup
    @inject
    async def configure_engine(logger: Logger):
        engine.config(url)
