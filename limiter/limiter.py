from typing import Callable, AsyncContextManager, Any, ContextManager, Awaitable
from contextlib import contextmanager, asynccontextmanager
from asyncio import sleep as aiosleep
from inspect import iscoroutinefunction
from functools import wraps
from time import sleep
import logging

from token_bucket import Limiter, MemoryStorage


DEFAULT_BUCKET = b"default"
CONSUME_TOKENS = 1.1
RATE = 2
CAPACITY = 3


def get_limiter(rate: float = RATE, capacity: float = CAPACITY) -> Limiter:
    """
    Returns Limiter object that implements a token-bucket algorithm.
    
    """
    
    return Limiter(rate, capacity, MemoryStorage())


def limit(limiter: Limiter, bucket: bytes = DEFAULT_BUCKET, consume: float = CONSUME_TOKENS) -> Callable[[Callable], Callable]:
    """
    Rate-limiting decorator for synchronous callables and asynchronous coroutines. 
    
    """
    
    def wrapper(func) -> Callable:
        if iscoroutinefunction(func):
            @wraps(func)
            async def new_coroutine(*a, **kw) -> Awaitable:
                async with async_limit_rate(limiter, bucket, consume):
                    return await func(*a, **kw)
            return new_coroutine
        
        elif callable(func):
            @wraps(func)
            def new_func(*a, **kw) -> Any:
                with limit_rate(limiter, bucket, consume):
                    return func(*a, **kw)
            return new_func

        else:
            raise ValueError(f"Can only decorate callables and coroutines.")

    return wrapper


@asynccontextmanager
async def async_limit_rate(limiter: Limiter, bucket: bytes = DEFAULT_BUCKET, consume: float = CONSUME_TOKENS) -> AsyncContextManager[Limiter]:
    """
    Rate-limiting asynchronous context manager.
    
    """
    
    while not limiter.consume(bucket, consume):
        tokens = limiter._storage.get_token_count(bucket)
        sleep_for = (consume - tokens) / limiter._rate
            
        if sleep_for < 0:
            break
            
        logging.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        await aiosleep(sleep_for)
    yield limiter


@contextmanager
def limit_rate(limiter: Limiter, bucket: bytes = DEFAULT_BUCKET, consume: float = CONSUME_TOKENS) -> ContextManager[Limiter]:
    """
    Thread-safe rate-limiting context manager.
    
    """
    
    while not limiter.consume(bucket, consume):
        tokens = limiter._storage.get_token_count(bucket)
        sleep_for = (consume - tokens) / limiter._rate

        if sleep_for < 0:
            break
            
        logging.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        sleep(sleep_for)
    yield limiter
