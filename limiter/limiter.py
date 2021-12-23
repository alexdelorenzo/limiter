from __future__ import annotations
from typing import Callable, AsyncContextManager, Any, \
    ContextManager, Awaitable, Union, Coroutine, Final, TypeVar, \
    ParamSpec
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


P = ParamSpec('P')
T = TypeVar('T')

Decoratable = Callable[P, T] | Callable[P, Awaitable[T]]
Decorated = Decoratable
Decorator = Callable[[Decoratable[P, T]], Decorated[P, T]]

Bucket = bytes
BucketName = Bucket | str


DEFAULT_BUCKET: Final[Bucket] = b"default"


def _get_bucket(name: BucketName) -> Bucket:
    match name:
        case bytes():
            return name

        case str():
            return name.encode()

        case _:
            raise ValueError('Names must be strings or bytes.')


def get_limiter(rate: float = RATE, capacity: float = CAPACITY) -> Limiter:
    """
    Returns Limiter object that implements a token-bucket algorithm.
    """

    return Limiter(rate, capacity, MemoryStorage())


@dataclass
class limit(AbstractContextManager, AbstractAsyncContextManager):
    """
    Rate-limiting blocking and non-blocking context-manager and decorator.
    """

    limiter: Limiter
    bucket: BucketName = DEFAULT_BUCKET
    consume: int | float = CONSUME_TOKENS

    def __post_init__(self):
        self.bucket: Bucket = _get_bucket(self.bucket)

    def __call__(self, func: Decoratable[P, T]) -> Decorated[P, T]:
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
    BucketName: BucketName = DEFAULT_BUCKET, 
    consume: int | float = CONSUME_TOKENS
) -> Decorator[P, T]:
    """
    Rate-limiting decorator for synchronous and asynchronous callables. 
    """
    bucket: Bucket = _get_bucket(bucket)

    def wrapper(func: Decoratable[P, T]) -> Decorated[P, T]:
        if iscoroutinefunction(func):
            @wraps(func)
            async def new_coroutine_func(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
                async with async_limit_rate(limiter, bucket, consume):
                    return await func(*args, **kwargs)

            return new_coroutine_func

        elif callable(func):
            @wraps(func)
            def new_func(*args: P.args, **kwargs: P.kwargs) -> T:
                with limit_rate(limiter, bucket, consume):
                    return func(*args, **kwargs)

            return new_func

        else:
            raise ValueError(f"Can only decorate callables and coroutine functions.")

    return wrapper


@asynccontextmanager
async def async_limit_rate(
    limiter: Limiter, 
    bucket: BucketName = DEFAULT_BUCKET, 
    consume: int | float = CONSUME_TOKENS
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
    bucket: BucketName = DEFAULT_BUCKET, 
    consume: int | float = CONSUME_TOKENS
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
