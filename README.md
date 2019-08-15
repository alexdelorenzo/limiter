# limiter

Rate-limiting asynchronous and synchronous decorators and context managers that implement the token-bucket algorithm.

 - Thread-safe, with no need for a timer thread
 - Control burst requests 
 

# Installation

## Requirements

 - Python 3.7+
 
## Installing from PyPI

```bash
pip3 install limiter
```

# Usage

```python3
from requests import get, Response
from limiter import get_limiter, limit, limit_rate, async_limit_rate
from asyncio import sleep

REFRESH_RATE = 2
BURST = 3
limiter = get_limiter(rate=REFRESH_RATE, capacity=BURST)


@limit(limiter)
def get_page(url: str) -> Response:
    return get(url)


@limit(limiter, consume=2)
async def example():
    await sleep(0.1)


def do_stuff():
    # do stuff
    
    with limit_rate(limiter, consume=1.5):
        # do expensive stuff
        pass


async def do_stuff():
    # do stuff
    
    async with async_limit_rate(limiter):
        # do expensive stuff
        pass
```