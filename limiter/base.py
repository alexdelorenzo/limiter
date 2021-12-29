from __future__ import annotations
from typing import Final, TypeVar, ParamSpec

from token_bucket import Limiter as _Limiter, MemoryStorage


WAKE_UP: Final[int] = 0


P = ParamSpec('P')
T = TypeVar('T')

Decoratable = Callable[P, T] | Callable[P, Awaitable[T]]
Decorated = Decoratable
Decorator = Callable[[Decoratable[P, T]], Decorated[P, T]]

Bucket = bytes
BucketName = Bucket | str
TokenAmount = int | float


CONSUME_TOKENS: Final[TokenAmount] = 1
CAPACITY: Final[TokenAmount] = 3
RATE: Final[TokenAmount] = 2

DEFAULT_BUCKET: Final[Bucket] = b"default"


def _get_bucket(name: BucketName) -> Bucket:
    match name:
        case bytes():
            return name

        case str():
            return name.encode()

    raise ValueError('Name must be a string or bytes.')


def _get_limiter(rate: TokenAmount = RATE, capacity: TokenAmount = CAPACITY) -> _Limiter:
    """
    Returns _Limiter object that implements a token-bucket algorithm.
    """

    return _Limiter(rate, capacity, MemoryStorage())


def _get_bucket_limiter(bucket: BucketName, limiter: Limiter) -> tuple[Bucket, _Limiter]:
    bucket: Bucket = _get_bucket(bucket)

    if isinstance(limiter, Limiter):
        limiter: _Limiter = limiter.limiter

    return bucket, limiter

