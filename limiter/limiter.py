from __future__ import annotations
from typing import Callable, AsyncContextManager, Any, \
    ContextManager, Awaitable, Union, Coroutine, Final
from contextlib import contextmanager, asynccontextmanager, \
    AbstractContextManager, AbstractAsyncContextManager
from asyncio import sleep as aiosleep
from inspect import iscoroutinefunction
from dataclasses import dataclass
from functools import wraps
from time import sleep
import logging

from token_bucket import Limiter, MemoryStorage


CONSUME_TOKENS: Final[int] = 1
CAPACITY: Final[int] = 3
RATE: Final[int] = 2
WAKE_UP: Final[int] = 0


Bucket = bytes
UserBucket = Bucket | str
Decoratable = Callable | Coroutine  # can decorate these types


DEFAULT_BUCKET: Final[Bucket] = b"default"


def _get_bucket(bucket: UserBucket) -> Bucket:
    match bucket:
        case bytes():
            return bucket
        
        case str():
            return bucket.encode()
        
        case _:
            raise ValueError('Bucket names must be strings or bytes.')


def get_limiter(rate: float = RATE, capacity: float = CAPACITY) -> Limiter:
    """
    Returns Limiter object that implements a token-bucket algorithm.
    """
    
    return Limiter(rate, capacity, MemoryStorage())


@dataclass
class limit(AbstractContextManager, AbstractAsyncContextManager):
    """
    Rate-limiting synchronous/asynchronous context manager and decorator.
    """

    limiter: Limiter
    bucket: UserBucket = DEFAULT_BUCKET
    consume: float = CONSUME_TOKENS
    
    def __post_init__(self):
        self.bucket: Bucket = _get_bucket(self.bucket)
        
    def __call__(self, func: Decoratable) -> Decoratable:
        wrapper = limit_calls(self.limiter, self.bucket, self.consume)
        return wrapper(func)

    def __enter__(self) -> ContextManager[Limiter]:
        with limit_rate(self.limiter, self.bucket, self.consume) as limiter:
            return limiter
    
    def __exit__(self, *args):
        pass
    
    async def __aenter__(self) -> Awaitable[AsyncContextManager[Limiter]]:
        async with async_limit_rate(self.limiter, self.bucket, self.consume) as limiter:
            return limiter
        
    async def __aexit__(self, *args):
        pass

    

def limit_calls(
    limiter: Limiter, 
    UserBucket: UserBucket = DEFAULT_BUCKET, 
    consume: float = CONSUME_TOKENS
) -> Callable[[Decoratable], Decoratable]:
    """
    Rate-limiting decorator for synchronous and asynchronous callables. 
    """
    bucket: Bucket = _get_bucket(bucket)
    
    def wrapper(func: Decoratable) -> Decoratable:
        if iscoroutinefunction(func):
            @wraps(func)
            async def new_coroutine_func(*a, **kw) -> Awaitable[Any]:
                async with async_limit_rate(limiter, bucket, consume):
                    return await func(*a, **kw)
                
            return new_coroutine_func
        
        elif callable(func):
            @wraps(func)
            def new_func(*a, **kw) -> Any:
                with limit_rate(limiter, bucket, consume):
                    return func(*a, **kw)
                
            return new_func

        else:
            raise ValueError(f"Can only decorate callables and coroutine functions.")

    return wrapper


@asynccontextmanager
async def async_limit_rate(
    limiter: Limiter, 
    bucket: UserBucket = DEFAULT_BUCKET, 
    consume: float = CONSUME_TOKENS
) -> AsyncContextManager[Limiter]:
    """
    Rate-limiting asynchronous context manager.
    """
    bucket: Bucket = _get_bucket(bucket)
    
    while not limiter.consume(bucket, consume):
        tokens = limiter._storage.get_token_count(bucket)
        sleep_for = (consume - tokens) / limiter._rate
            
        if sleep_for <= WAKE_UP:
            break
            
        logging.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        await aiosleep(sleep_for)
 
    yield limiter


@contextmanager
def limit_rate(
    limiter: Limiter, 
    bucket: UserBucket = DEFAULT_BUCKET, 
    consume: float = CONSUME_TOKENS
) -> ContextManager[Limiter]:
    """
    Thread-safe rate-limiting context manager.
    """
    bucket: Bucket = _get_bucket(bucket)
    
    while not limiter.consume(bucket, consume):
        tokens = limiter._storage.get_token_count(bucket)
        sleep_for = (consume - tokens) / limiter._rate

        if sleep_for <= WAKE_UP:
            break
            
        logging.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        sleep(sleep_for)

    yield limiter

