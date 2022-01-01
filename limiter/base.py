from __future__ import annotations
from typing import Final, TypeVar, ParamSpec, Callable, Awaitable
from random import random

from token_bucket import Limiter as _Limiter, MemoryStorage


WAKE_UP: Final[int] = 0


P = ParamSpec('P')
T = TypeVar('T')

Decoratable = Callable[P, T] | Callable[P, Awaitable[T]]
Decorated = Decoratable
Decorator = Callable[[Decoratable[P, T]], Decorated[P, T]]

Bucket = bytes
BucketName = Bucket | str
Tokens = int | float
Duration = int | float
UnitsInSecond = Duration


CONSUME_TOKENS: Final[Tokens] = 1
CAPACITY: Final[Tokens] = 3
RATE: Final[Tokens] = 2
MS_IN_SEC: Final[UnitsInSecond] = 1000

DEFAULT_BUCKET: Final[Bucket] = b"default"


def _get_bucket(name: BucketName) -> Bucket:
    match name:
        case bytes():
            return name

        case str():
            return name.encode()

    raise ValueError('Name must be a string or bytes.')


def _get_limiter(rate: Tokens = RATE, capacity: Tokens = CAPACITY) -> _Limiter:
    """
    Returns _Limiter object that implements a token-bucket algorithm.
    """

    return _Limiter(rate, capacity, MemoryStorage())


def _get_bucket_limiter(bucket: BucketName, limiter: Limiter) -> tuple[Bucket, _Limiter]:
    bucket: Bucket = _get_bucket(bucket)

    if not isinstance(limiter, _Limiter):
        limiter: _Limiter = limiter.limiter

    return bucket, limiter


def _get_sleep_duration(
    consume: Tokens,
    tokens: Tokens,
    rate: Tokens,
    jitter: bool = True,
    units: UnitsInSecond = MS_IN_SEC
) -> Duration:
    """Increase contention by adding jitter to sleep duration"""
    duration: Duration = (consume - token) / rate

    if jitter:
        amount: Duration = random() / units
        return duration - amount

    return duration
