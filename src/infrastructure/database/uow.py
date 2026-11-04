from types import TracebackType
from typing import Optional, Self, Type

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.uow import UnitOfWork


class UnitOfWorkImpl(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        logger.debug("SQL transaction started")
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type:
            await self.rollback()
        # Session lifetime is owned by the request-scoped Dishka provider.
        # Keeping it open here allows nested application interactors to share
        # one request safely without invalidating the outer transaction.

    async def commit(self) -> None:
        await self.session.commit()
        logger.debug("SQL transaction committed")

    async def rollback(self) -> None:
        await self.session.rollback()
        logger.warning("SQL transaction rolled back")
