from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import Callable, Type

from wintry.ioc.container import IGlooContainer, igloo

from wintrymodels.dbcontext import DataContext, SyncDataContext


def atomic(
        *,
        with_context: Type[DataContext] | Type[SyncDataContext],
        container: IGlooContainer = igloo
):
    def decorator(fn: Callable):
        @wraps(fn)
        async def transactional_function(*args, **kwargs):
            # get the DbContext from the container
            context: DataContext = container[with_context]
            assert isinstance(context, DataContext), Exception(
                "Async atomic function should depend on DbContext"
            )
            context.begin()
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                await context.rollback()
                raise e
            finally:
                await context.commit()

        @wraps(fn)
        def sync_transaction(*args, **kwargs):
            # get the DbContext from the container
            context: SyncDataContext = container[with_context]
            assert isinstance(context, SyncDataContext), Exception(
                "Sync atomic function should depend on SyncDbContext"
            )
            context.begin()
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                context.rollback()
                raise e
            finally:
                context.commit()

        sig = signature(fn)
        if iscoroutinefunction(fn):
            setattr(transactional_function, "__signature__", sig)
            return transactional_function
        else:
            setattr(sync_transaction, "__signature__", sig)
            return sync_transaction

    return decorator
