from __future__ import annotations

import logging
from operator import add, sub
from random import choice, randrange
from typing import Awaitable, Callable, Final, ParamSpec, TypeVar

from token_bucket import Limiter as TokenBucket, MemoryStorage


log = logging.getLogger(__name__)


WAKE_UP: Final[int] = 0


P = ParamSpec('P')
T = TypeVar('T')

Decoratable = Callable[P, T] | Callable[P, Awaitable[T]]
Decorated = Decoratable
Decorator = Callable[[Decoratable[P, T]], Decorated[P, T]]

Bucket = bytes
BucketName = Bucket | str
Num = int | float
Tokens = Num
Duration = Num
UnitsInSecond = Duration
JitterRange = range | tuple[int, int] | tuple[int, int, int]
Jitter = int | bool | JitterRange
JitterDirection = Callable[[Num, Num], Num]


CONSUME_TOKENS: Final[Tokens] = 1
RATE: Final[Tokens] = 2
CAPACITY: Final[Tokens] = 3
MS_IN_SEC: Final[UnitsInSecond] = 1000

DEFAULT_BUCKET: Final[Bucket] = b"default"
DEFAULT_JITTER: Final[Jitter] = False
DEFAULT_RANGE: Final[range] = range(50)

JITTER_DIRECTIONS: Final[tuple[JitterDirection, ...]] = add, sub


def _get_bucket(name: BucketName) -> Bucket:
  match name:
    case bytes():
      return name

    case str():
      return name.encode()

  raise TypeError('Name must be bytes or a bytes-encodable string.')


def _get_limiter(rate: Tokens = RATE, capacity: Tokens = CAPACITY) -> TokenBucket:
  """
  Returns TokenBucket object that implements a token-bucket algorithm.
  """

  return TokenBucket(rate, capacity, MemoryStorage())


def _get_bucket_limiter(bucket: BucketName, limiter: 'Limiter' | TokenBucket) -> tuple[Bucket, TokenBucket]:
  bucket: Bucket = _get_bucket(bucket)

  if not isinstance(limiter, TokenBucket):
    limiter: TokenBucket = limiter.limiter

  return bucket, limiter


def _get_sleep_duration(
  consume: Tokens,
  tokens: Tokens,
  rate: Tokens,
  jitter: Jitter = DEFAULT_JITTER,
  units: UnitsInSecond = MS_IN_SEC
) -> Duration:
  """Increase contention by adding jitter to sleep duration"""
  log.debug(f'{consume=}, {tokens=}, {rate=}, {jitter=}, {units=}')
  duration: Duration = (consume - tokens) / rate
  log.debug(f'{duration=}')

  operation = choice(JITTER_DIRECTIONS)

  match jitter:
    case int() | float():
      return operation(duration, jitter)

    case range() | bool() if jitter:
      if jitter is True:
        jitter: range = DEFAULT_RANGE

      amount: Duration = randrange(jitter.start, jitter.stop, jitter.step) / units
      return operation(duration, amount)

    case start, stop:
      amount: Duration = randrange(start, stop) / units
      return operation(duration, amount)

    case start, stop, step:
      amount: Duration = randrange(start, stop, step) / units
      return operation(duration, amount)

  return duration
