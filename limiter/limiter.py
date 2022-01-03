from __future__ import annotations

from typing import AsyncContextManager, ContextManager, Awaitable
from contextlib import (
    AbstractContextManager, AbstractAsyncContextManager,
    contextmanager, asynccontextmanager
)
from asyncio import sleep as aiosleep, iscoroutinefunction
from dataclasses import dataclass, asdict
from functools import wraps
from logging import debug
from enum import auto
from time import sleep
from abc import ABC

from strenum import StrEnum  # type: ignore
from token_bucket import Limiter as _Limiter  # type: ignore

from .base import (
    WAKE_UP, RATE, CAPACITY, CONSUME_TOKENS, DEFAULT_BUCKET,
    Tokens, Decoratable, Decorated, Decorator, P, T,
    BucketName, _get_limiter, _get_bucket_limiter,
    _get_sleep_duration
)


LIM_KEY: str = 'limiter'


Attrs = dict[str, Tokens | BucketName | _Limiter]


class LimiterBase(ABC):
    consume: Tokens
    bucket: BucketName

    limiter: _Limiter


class LimiterCtxMixin(
    LimiterBase,
    AbstractContextManager,
    AbstractAsyncContextManager
):
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


class AttrName(StrEnum):
    rate: str = auto()
    capacity: str = auto()

    consume: str = auto()
    bucket: str = auto()

    limiter: str = auto()


@dataclass
class Limiter(LimiterCtxMixin):
    rate: Tokens = RATE
    capacity: Tokens = CAPACITY

    consume: Tokens | None = None
    bucket: BucketName = DEFAULT_BUCKET

    limiter: _Limiter | None = None

    def __post_init__(self):
      if self.limiter is None:
        limiter = _get_limiter(self.rate, self.capacity)
        self.limiter = limiter

      if self.consume is None:
        self.consume = CONSUME_TOKENS

    def __call__(
      self,
      func_or_consume: Decoratable[P, T] | Tokens | None = None,
      bucket: BucketName | None = None,
      **kwargs,
    ) -> Decorated[P, T] | Limiter:
      if func_or_consume is None:
        pass

      elif callable(func_or_consume):
        wrapper = limit_calls(self.limiter, self.consume, self.bucket)
        return wrapper(func_or_consume)

      elif not isinstance(func_or_consume, Tokens):
        raise ValueError(f'First argument must be a callable or {Tokens}')

      if AttrName.rate in kwargs or AttrName.capacity in kwargs:
        raise ValueError('Create a new limiter with the new}() method or Limiter class')

      consume: Tokens = func_or_consume
      new_attrs: Attrs = self.attrs

      if consume:
        new_attrs[AttrName.consume] = consume

      if bucket:
        new_attrs[AttrName.bucket] = bucket

      new_attrs |= kwargs

      return Limiter(**new_attrs, limiter=self.limiter)

    @property
    def attrs(self) -> Attrs:
      attrs = asdict(self)
      attrs.pop(LIM_KEY, None)

      return attrs

    def new(self, **new_attrs: Attrs):
      updated_attrs = self.attrs | new_attrs

      return Limiter(**updated_attrs)


def limit_calls(
    limiter: Limiter,
    consume: Tokens = CONSUME_TOKENS,
    bucket: BucketName = DEFAULT_BUCKET,
) -> Decorator[P, T]:
    """
    Rate-limiting decorator for synchronous and asynchronous callables.
    """
    lim_wrapper = limiter
    bucket, limiter = _get_bucket_limiter(bucket, limiter)

    def wrapper(func: Decoratable[P, T]) -> Decorated[P, T]:
        if iscoroutinefunction(func):
            @wraps(func)
            async def new_coroutine_func(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
                async with async_limit_rate(limiter, consume, bucket):
                    return await func(*args, **kwargs)

            new_coroutine_func.limiter = lim_wrapper
            return new_coroutine_func

        elif callable(func):
            @wraps(func)
            def new_func(*args: P.args, **kwargs: P.kwargs) -> T:
                with limit_rate(limiter, consume, bucket):
                    return func(*args, **kwargs)

            new_func.limiter = lim_wrapper
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

    # minimize attribute look ups in loop
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

    # minimize attribute look ups in loop
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
