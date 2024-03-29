from __future__ import annotations

import logging
from abc import ABC
from asyncio import iscoroutinefunction, sleep as aiosleep
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass
from enum import auto
from functools import wraps
from time import sleep
from typing import AsyncContextManager, Awaitable, ContextManager, TypedDict, cast

from strenum import StrEnum  # type: ignore
from token_bucket import Limiter as TokenBucket  # type: ignore

from .base import (
  BucketName, CAPACITY, CONSUME_TOKENS, DEFAULT_BUCKET, DEFAULT_JITTER, Decoratable, Decorated, Decorator, Jitter,
  MS_IN_SEC, P, RATE, T, Tokens, UnitsInSecond, WAKE_UP, _get_bucket_limiter, _get_limiter, _get_sleep_duration,
)


log = logging.getLogger(__name__)


class Attrs(TypedDict):
  consume: Tokens
  bucket: BucketName

  limiter: TokenBucket
  jitter: Jitter
  units: UnitsInSecond


class LimiterBase(ABC):
  consume: Tokens
  bucket: BucketName

  limiter: TokenBucket
  jitter: Jitter
  units: UnitsInSecond


class LimiterContextManager(
  LimiterBase,
  AbstractContextManager,
  AbstractAsyncContextManager
):
  def __enter__(self) -> ContextManager[Limiter]:
    with limit_rate(self.limiter, self.consume, self.bucket, self.jitter, self.units) as limiter:
      return limiter

  def __exit__(self, *args):
    pass

  async def __aenter__(self) -> AsyncContextManager[Limiter]:
    async with async_limit_rate(self.limiter, self.consume, self.bucket, self.jitter, self.units) as limiter:
      return limiter

  async def __aexit__(self, *args):
    pass


class AttrName(StrEnum):
  rate: str = auto()
  capacity: str = auto()

  consume: str = auto()
  bucket: str = auto()

  limiter: str = auto()
  jitter: str = auto()
  units: str = auto()


@dataclass
class Limiter(LimiterContextManager):
  rate: Tokens = RATE
  capacity: Tokens = CAPACITY

  consume: Tokens | None = None
  bucket: BucketName = DEFAULT_BUCKET

  limiter: TokenBucket | None = None
  jitter: Jitter = DEFAULT_JITTER
  units: UnitsInSecond = MS_IN_SEC

  def __post_init__(self):
    if self.limiter is None:
      self.limiter = _get_limiter(self.rate, self.capacity)

    if self.consume is None:
      self.consume = CONSUME_TOKENS

  def __call__(
    self,
    func_or_consume: Decoratable[P, T] | Tokens | None = None,
    bucket: BucketName | None = None,
    jitter: Jitter | None = None,
    units: UnitsInSecond | None = None,
    **attrs: Attrs,
  ) -> Decorated[P, T] | Limiter:
    if callable(func_or_consume):
      func: Decoratable = cast(Decoratable, func_or_consume)
      wrapper = limit_calls(self, self.consume, self.bucket)

      return wrapper(func)

    elif func_or_consume and not isinstance(func_or_consume, Tokens):
      raise TypeError(f'First argument must be callable or {Tokens}')

    if AttrName.rate in attrs or AttrName.capacity in attrs:
      raise ValueError('Create a new limiter with the new() method or Limiter class')

    consume: Tokens = cast(Tokens, func_or_consume)
    new_attrs = self._get_new_attrs(attrs, bucket, consume, jitter, units)

    return Limiter(**new_attrs, limiter=self.limiter)

  def _get_new_attrs(
    self,
    attrs: Attrs,
    bucket: BucketName,
    consume: Tokens,
    jitter: Jitter,
    units: UnitsInSecond
  ) -> Attrs:
    new_attrs: Attrs = self.attrs

    if consume:
      new_attrs[AttrName.consume] = consume

    if bucket:
      new_attrs[AttrName.bucket] = bucket

    if jitter:
      new_attrs[AttrName.jitter] = jitter

    if units:
      new_attrs[AttrName.units] = units

    new_attrs |= attrs

    return new_attrs

  @property
  def attrs(self) -> Attrs:
    attrs = asdict(self)
    attrs.pop(AttrName.limiter, None)

    return attrs

  def new(self, **attrs: Attrs):
    new_attrs = self.attrs | attrs

    return Limiter(**new_attrs)


def limit_calls(
  limiter: Limiter,
  consume: Tokens = CONSUME_TOKENS,
  bucket: BucketName = DEFAULT_BUCKET,
  jitter: Jitter = DEFAULT_JITTER,
  units: UnitsInSecond = MS_IN_SEC,
) -> Decorator[P, T]:
  """
  Rate-limiting decorator for synchronous and asynchronous callables.
  """
  lim_wrapper: Limiter = limiter

  bucket, limiter = _get_bucket_limiter(bucket, limiter)
  limiter: TokenBucket = cast(TokenBucket, limiter)

  def decorator(func: Decoratable[P, T]) -> Decorated[P, T]:
    if iscoroutinefunction(func):
      @wraps(func)
      async def new_coroutine_func(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
        async with async_limit_rate(limiter, consume, bucket, jitter, units):
          return await func(*args, **kwargs)

      new_coroutine_func.limiter = lim_wrapper
      return new_coroutine_func

    elif callable(func):
      @wraps(func)
      def new_func(*args: P.args, **kwargs: P.kwargs) -> T:
        with limit_rate(limiter, consume, bucket, jitter, units):
          return func(*args, **kwargs)

      new_func.limiter = lim_wrapper
      return new_func

    else:
      raise ValueError("Can only decorate callables and coroutine functions.")

  return decorator


@asynccontextmanager
async def async_limit_rate(
  limiter: Limiter,
  consume: Tokens = CONSUME_TOKENS,
  bucket: BucketName = DEFAULT_BUCKET,
  jitter: Jitter = DEFAULT_JITTER,
  units: UnitsInSecond = MS_IN_SEC,
) -> AsyncContextManager[Limiter]:
  """
  Rate-limiting asynchronous context manager.
  """
  lim_wrapper: Limiter = limiter

  bucket, limiter = _get_bucket_limiter(bucket, limiter)
  limiter: TokenBucket = cast(TokenBucket, limiter)

  # minimize attribute look ups in loop
  get_tokens = limiter._storage.get_token_count
  lim_consume = limiter.consume
  rate = limiter._rate

  while not lim_consume(bucket, consume):
    tokens = get_tokens(bucket)
    sleep_for = _get_sleep_duration(consume, tokens, rate, jitter, units)

    if sleep_for <= WAKE_UP:
      break

    log.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
    await aiosleep(sleep_for)

  yield lim_wrapper


@contextmanager
def limit_rate(
  limiter: Limiter,
  consume: Tokens = CONSUME_TOKENS,
  bucket: BucketName = DEFAULT_BUCKET,
  jitter: Jitter = DEFAULT_JITTER,
  units: UnitsInSecond = MS_IN_SEC,
) -> ContextManager[Limiter]:
  """
  Thread-safe rate-limiting context manager.
  """
  lim_wrapper: Limiter = limiter

  bucket, limiter = _get_bucket_limiter(bucket, limiter)
  limiter: TokenBucket = cast(TokenBucket, limiter)

  # minimize attribute look ups in loop
  get_tokens = limiter._storage.get_token_count
  lim_consume = limiter.consume
  rate = limiter._rate

  while not lim_consume(bucket, consume):
    tokens = get_tokens(bucket)
    sleep_for = _get_sleep_duration(consume, tokens, rate, jitter, units)

    if sleep_for <= WAKE_UP:
      break

    log.debug(f'Rate limit reached. Sleeping for {sleep_for}s.')
    sleep(sleep_for)

  yield lim_wrapper
