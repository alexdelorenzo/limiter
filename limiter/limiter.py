from __future__ import annotations
from typing import AsyncContextManager, ContextManager, Awaitable, Type
from contextlib import contextmanager, asynccontextmanager, \
    AbstractContextManager, AbstractAsyncContextManager
from asyncio import sleep as aiosleep, iscoroutinefunction
from dataclasses import dataclass, asdict
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


LIM_KEY: str = 'limiter'


class LimitCtxManagerMixin(
  AbstractContextManager,
  AbstractAsyncContextManager
):
    limiter: Limiter
    consume: Tokens
    bucket: BucketName

    def __enter__(self) -> ContextManager[Limiter]:
        with limit_rate(self.limiter, self.consume, self.bucket) as limiter:
            return limiter

    def __exit__(self, *args):
        pass

    async def __aenter__(self) -> AsyncContextManager[Limiter]:
        async with async_limit_rate(self.limiter, self.consume, self.bucket) as limiter:
            return limiter

    async def __aexit__(self, *args):
        pass


@dataclass
class Limiter(LimitCtxManagerMixin):
    rate: Tokens = RATE
    capacity: Tokens = CAPACITY

    consume: Tokens | None = None
    bucket: BucketName = DEFAULT_BUCKET

    limiter: _Limiter | None = None

    def __post_init__(self):
      if self.limiter is None:
        limiter = _get_limiter(self.rate, self.capacity)
        self.limiter = limiter

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Decorated[P, T] | Limiter:
      match args:
        case func, *_ if callable(func):
          wrapper = limit_calls(self.limiter, self.consume, self.bucket)
          return wrapper(func)

      return Limiter(*args, **kwargs, limiter=self.limiter)

    def limit(
      self,
      consume: Tokens = CONSUME_TOKENS,
      bucket: BucketName = DEFAULT_BUCKET,
    ) -> Limiter:
      return Limiter(self.rate, self.capacity, consume, bucket, limiter=self.limiter)

    def new(self, **kwargs):
      current_attrs = asdict(self)
      new_attrs = {**current_attrs, **kwargs}
      new_attrs.pop(LIM_KEY, None)

      return Limiter(**new_attrs)

    def to_dict(self) -> dict[str, Tokens | BucketName | _Limiter]:
      return asdict(self)

    #@staticmethod
    #def static(
      #rate: Tokens = RATE,
      #capacity: Tokens = CAPACITY,
      #consume: Tokens = CONSUME_TOKENS,
      #bucket: BucketName = DEFAULT_BUCKET,
    #) -> limit:
      #limiter = Limiter(rate, capacity)
      #return limit(limiter, consume, bucket)


@dataclass
class limit(LimitCtxManagerMixin):
    """
    Rate-limiting blocking and non-blocking context-manager and decorator.
    """

    limiter: Limiter
    consume: Tokens = CONSUME_TOKENS
    bucket: BucketName = DEFAULT_BUCKET

    def __post_init__(self):
        self.bucket: Bucket = _get_bucket(self.bucket)

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

            new_coroutine_func.limiter = limiter
            return new_coroutine_func

        elif callable(func):
            @wraps(func)
            def new_func(*args: P.args, **kwargs: P.kwargs) -> T:
                with limit_rate(limiter, consume, bucket):
                    return func(*args, **kwargs)

            new_func.limiter = limiter
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
