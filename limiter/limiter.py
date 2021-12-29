from __future__ import annotations
from typing import AsyncContextManager, ContextManager, Awaitable, Type
from contextlib import contextmanager, asynccontextmanager, \
    AbstractContextManager, AbstractAsyncContextManager
from asyncio import sleep as aiosleep, iscoroutinefunction
from dataclasses import dataclass
from functools import wraps
from time import sleep
from logging import debug
from token_bucket import Limiter as _Limiter  # type: ignore

from .base import (
    Tokens, Decoratable, Decorated, Decorator, P, T, Bucket,
    BucketName, _get_limiter, _get_bucket, _get_bucket_limiter,
    _get_sleep_duration, WAKE_UP, RATE, CAPACITY, CONSUME_TOKENS,
    DEFAULT_BUCKET
)


@dataclass
class Limiter:
    rate: Tokens = RATE
    capacity: Tokens = CAPACITY

    limiter: _Limiter | None = None

    def __post_init__(self):
      limiter = _get_limiter(self.rate, self.capacity)
      self.limiter = limiter

    def limit(
      self,
      consume: Tokens = CONSUME_TOKENS,
      bucket: BucketName = DEFAULT_BUCKET,
    ) -> limit:
      return limit(self, consume, bucket)

    @staticmethod
    def static(
      rate: Tokens = RATE,
      capacity: Tokens = CAPACITY,
      consume: Tokens = CONSUME_TOKENS,
      bucket: BucketName = DEFAULT_BUCKET,
    ) -> limit:
      limiter = Limiter(rate, capacity)
      return limit(limiter, consume, bucket)


@dataclass
class limit(AbstractContextManager, AbstractAsyncContextManager):
    """
    Rate-limiting blocking and non-blocking context-manager and decorator.
    """

    limiter: Limiter
    consume: Tokens = CONSUME_TOKENS
    bucket: BucketName = DEFAULT_BUCKET

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

    async def __aenter__(self) -> AsyncContextManager[Limiter]:
        async with async_limit_rate(self.limiter, self.bucket, self.consume) as limiter:
            return limiter

    async def __aexit__(self, *args):
        pass

    @classmethod
    def static(
      cls: Type[limit],
      rate: Tokens = RATE,
      capacity: Tokens = CAPACITY,
      bucket: BucketName = DEFAULT_BUCKET,
      consume: Tokens = CONSUME_TOKENS,
    ) -> limit:
      limiter = _get_limiter(rate, capacity)
      return cls(limiter, consume, bucket)


def limit_calls(
    limiter: Limiter,
    consume: Tokens = CONSUME_TOKENS,
    bucket: BucketName = DEFAULT_BUCKET,
) -> Decorator[P, T]:
    """
    Rate-limiting decorator for synchronous and asynchronous callables.
    """
    bucket, limiter = _get_bucket_limiter(bucket, limiter)

    def wrapper(func: Decoratable[P, T]) -> Decorated[P, T]:
        if iscoroutinefunction(func):
            @wraps(func)
            async def new_coroutine_func(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
                async with async_limit_rate(limiter, consume, bucket):
                    return await func(*args, **kwargs)

            return new_coroutine_func

        elif callable(func):
            @wraps(func)
            def new_func(*args: P.args, **kwargs: P.kwargs) -> T:
                with limit_rate(limiter, consume, bucket):
                    return func(*args, **kwargs)

            return new_func

        else:
            raise ValueError("Can only decorate callables and coroutine functions.")

    return wrapper


@asynccontextmanager
async def async_limit_rate(
    limiter: Limiter,
    consume: Tokens = CONSUME_TOKENS,
    bucket: BucketName = DEFAULT_BUCKET,
) -> AsyncContextManager[Limiter]:
    """
    Rate-limiting asynchronous context manager.
    """
    bucket, limiter = _get_bucket_limiter(bucket, limiter)

    # minimize attribute look-ups in tight loop
    get_tokens = limiter._storage.get_token_count
    lim_consume = limiter.consume
    rate = limiter._rate

    while not lim_consume(bucket, consume):
        tokens = get_tokens(bucket)
        sleep_for = _get_sleep_duration(consume, tokens, rate, jitter=True)

        if sleep_for <= WAKE_UP:
            break

        debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        await aiosleep(sleep_for)

    yield limiter


@contextmanager
def limit_rate(
    limiter: Limiter,
    consume: Tokens = CONSUME_TOKENS,
    bucket: BucketName = DEFAULT_BUCKET,
) -> ContextManager[Limiter]:
    """
    Thread-safe rate-limiting context manager.
    """
    bucket, limiter = _get_bucket_limiter(bucket, limiter)

    # minimize attribute look-ups in tight loop
    get_tokens = limiter._storage.get_token_count
    lim_consume = limiter.consume
    rate = limiter._rate

    while not lim_consume(bucket, consume):
        tokens = get_tokens(bucket)
        sleep_for = _get_sleep_duration(consume, tokens, rate, jitter=True)

        if sleep_for <= WAKE_UP:
            break

        debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
        sleep(sleep_for)

    yield limiter
