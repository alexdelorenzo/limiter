# limiter

Rate-limiting thread-safe and asynchronous decorators and context managers that implement the token-bucket algorithm.

 - [Thread-safe, with no need for a timer thread](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm)
 - Control burst requests
 - Control average request rate
 - Easy to use

# Installation

## Requirements

 - Python 3.7+
 
## Installing from PyPI

```bash
python3 -m pip install limiter
```

# Usage

```python3
import time
import asyncio

from limiter import get_limiter, limit


REFRESH_RATE: int = 2
BURST_RATE: int = 3


limiter = get_limiter(rate=REFRESH_RATE, capacity=BURST_RATE)


@limit(limiter)
def download_page(url: str) -> bytes:
    time.sleep(1)
    ...


@limit(limiter, consume=2)
async def download_page(page: bytes) -> bytes:
    await asyncio.sleep(1)
    ...


def send_page(page: bytes):
    with limit(limiter, consume=1.5):
        ...


async def send_page(page: bytes):
    async with limit(limiter):
        ...
        

@limit(limiter, bucket=b'messages')
def send_email(page: bytes):
    ...
    


async def send_email(page: bytes):
    async with limit(limiter, bucket=b'messages'):
        ...
```

# License

See [`LICENSE`](/LICENSE). If you'd like to use this project with a different license, please get in touch.
