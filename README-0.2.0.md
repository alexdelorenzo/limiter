# ⏲️ Easy rate limiting for Python

`limiter` makes it easy to add [rate limiting](https://en.wikipedia.org/wiki/Rate_limiting) to Python projects, using a [token bucket](https://en.wikipedia.org/wiki/Token_bucket) algorithm. `limiter` can provide Python projects and scripts with:
  - Rate limiting thread-safe [decorators](https://www.python.org/dev/peps/pep-0318/)
  - Rate limiting async decorators
  - Rate limiting thread-safe [context-managers](https://www.python.org/dev/peps/pep-0343/)
  - Rate limiting [async context-managers](https://www.python.org/dev/peps/pep-0492/#asynchronous-context-managers-and-async-with)

Here are a few benefits of using `limiter`:
 - Easily control burst and average request rates
 - `limiter` is [thread-safe, with no need for a timer thread](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm)
 - Has a simple API that takes advantage of Python's features, idioms and [type hinting](https://www.python.org/dev/peps/pep-0483/)

# Usage
You can define [dynamic](#dynamic-limit) and [static](#static-limit) limiters, and use them across your project.

### Dynamic `limit`
You can define a limiter with a set `rate` and `capacity`. Then you can consume a dynamic amount of tokens from different buckets using `limit()`:
```python3
from limiter import get_limiter, limit


REFRESH_RATE: int = 2
BURST_RATE: int = 3
MSG_BUCKET: bytes = b'messages'


limiter = get_limiter(rate=REFRESH_RATE, capacity=BURST_RATE)


@limit(limiter)
def download_page(url: str) -> bytes:
    ...


@limit(limiter, consume=2)
async def download_page(url: str) -> bytes:
    ...


def send_page(page: bytes):
    with limit(limiter, consume=1.5):
        ...


async def send_page(page: bytes):
    async with limit(limiter):
        ...


@limit(limiter, bucket=MSG_BUCKET)
def send_email(to: str):
    ...


async def send_email(to: str):
    async with limit(limiter, bucket=MSG_BUCKET):
        ...
```

### Static `limit`
You can define a static `limit` and share it between blocks of code:
```python
limit_downloads = limit(limter, consume=2)


@limit_downloads
def download_page(url: str) -> bytes:
    ...


@limit_downloads
async def download_page(url: str) -> bytes:
    ...


def download_image(url: str) -> bytes:
    with limit_downloads:
        ...


async def download_image(url: str) -> bytes:
    async with limit_downloads:
        ...
```

# Installation
## Requirements
 - Python 3.7+
 
## Installing from PyPI
```bash
python3 -m pip install limiter
```

# License

See [`LICENSE`](/LICENSE). If you'd like to use this project with a different license, please get in touch.
