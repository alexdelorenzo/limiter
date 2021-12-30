# ⏲️ Easy rate limiting for Python

`limiter` makes it easy to add [rate limiting](https://en.wikipedia.org/wiki/Rate_limiting) to Python projects, using a [token bucket](https://en.wikipedia.org/wiki/Token_bucket) algorithm. `limiter` can provide Python projects and scripts with:
  - Rate limiting thread-safe [decorators](https://www.python.org/dev/peps/pep-0318/)
  - Rate limiting async decorators
  - Rate limiting thread-safe [context-managers](https://www.python.org/dev/peps/pep-0343/)
  - Rate limiting [async context-managers](https://www.python.org/dev/peps/pep-0492/#asynchronous-context-managers-and-async-with)

Here are a few benefits of using `limiter` and its features:
 - Easily control burst and average request rates
 - `limiter` is [thread-safe, with no need for a timer thread](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm)
 - `limiter` has a simple API that takes advantage of Python's features, idioms and [type hinting](https://www.python.org/dev/peps/pep-0483/)
 - `limiter` uses [jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) to help with contention

## Example
Here's an example of using a static limiter as a decorator and context manager:
```python
from aiohttp import ClientSession
from limiter import Limiter


limit_downloads = Limiter.static(rate=2, capacity=5, consume=2)


@limit_downloads
async def download_image(url: str) -> bytes:
  ...

# or

async def download_page(url: str) -> str:
  async with (
    limit_downloads,
    ClientSession() as session,
    session.get(url) as response,
  ):
    return await response.text()
```

# Usage
You can define [dynamic](#dynamic-limit) and [static](#static-limit) limiters, and use them across your project.

### Dynamic `limit`
You can define a limiter with a set `rate` and `capacity`. Then you can consume a dynamic amount of tokens from different buckets using `limit()`:
```python3
from limiter import limit, Limiter


REFRESH_RATE: int = 2
BURST_RATE: int = 3
MSG_BUCKET: bytes = b'messages'


limiter = Limiter(rate=REFRESH_RATE, capacity=BURST_RATE)


@limiter.limit()
def download_page(url: str) -> bytes:
    ...


@limiter.limit(consume=2)
async def download_page(url: str) -> bytes:
    ...


def send_page(page: bytes):
    with limiter.limit(consume=1.5):
        ...


async def send_page(page: bytes):
    async with limiter.limit():
        ...


@limiter.limit(bucket=MSG_BUCKET)
def send_email(to: str):
    ...


async def send_email(to: str):
    async with limiter.limit(bucket=MSG_BUCKET):
        ...
```

### Static `limit`
You can define a static `limit` and share it between blocks of code:
```python
# you can reuse existing limiters statically
limit_downloads = limiter.limit(consume=2)

# or you can define new static limiters
limit_downloads = Limiter.static(REFRESH_RATE, BURST_RATE, consume=2)


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
 - Python 3.10+ for versions `0.3.0` and up
 - Python 3.7+ for versions below `0.3.0`

## Install via PyPI
```bash
$ python3 -m pip install limiter
```

# License
See [`LICENSE`](/LICENSE). If you'd like to use this project with a different license, please get in touch.
