from __future__ import annotations
from typing import Final, TypeVar, ParamSpec, Callable, Awaitable
from random import random, randrange

from token_bucket import Limiter as TokenBucket, MemoryStorage


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


CONSUME_TOKENS: Final[Tokens] = 1
RATE: Final[Tokens] = 2
CAPACITY: Final[Tokens] = 3
MS_IN_SEC: Final[UnitsInSecond] = 1000

DEFAULT_BUCKET: Final[Bucket] = b"default"
DEFAULT_JITTER: Final[Jitter] = False


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


def _get_bucket_limiter(bucket: BucketName, limiter: 'Limiter') -> tuple[Bucket, TokenBucket]:
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
  duration: Duration = (consume - tokens) / rate

  match jitter:
    case int() | float():
      return duration - jitter

    case bool() if jitter:
      amount: Duration = random() / units
      return duration - amount

    case range():
      amount: Duration = randrange(jitter.start, jitter.stop, jitter.step) / units
      return duration - amount

    case start, end:
      amount: Duration = randrange(start, end) / units
      return duration - amount

    case start, end, step:
      amount: Duration = randrange(start, end, step) / units
      return duration - amount

  return duration
