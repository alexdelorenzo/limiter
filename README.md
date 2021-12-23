# limiter

Rate-limiting thread-safe and asynchronous decorators and context managers that implement the token-bucket algorithm.

 - [Thread-safe, with no need for a timer thread](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm)
 - Control burst requests
 - Control average request rate
 - Easy to use

# Usage
You can define a limiter with a set `rate` and `capacity`. Then you can consume a dynamic amount of tokens from different buckets using `limit`.
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

You can define a static `limit` and share it between blocks of code:
```python
limit_download = limit(limter, consume=2)


@limit_download
def download_page(url: str) -> bytes:
    ...


@limit_download
async def download_page(url: str) -> bytes:
    ...


def download_image(url: str) -> bytes:
    with limit_download:
        ...


async def download_image(url: str) -> bytes:
    async with limit_download:
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
