# limiter

Rate-limiting thread-safe and asynchronous decorators and context managers that implement the token-bucket algorithm.

 - Thread-safe, with no need for a timer thread
 - Control burst requests
 - Control average request rate
 - Easy to use

# Installation

## Requirements

 - Python 3.7+
 
## Installing from PyPI

```bash
pip3 install limiter
```

# Usage

```python3
from asyncio import sleep

from requests import get, Response
from limiter import get_limiter, limit


REFRESH_RATE = 2
BURST_RATE = 3


limiter = get_limiter(rate=REFRESH_RATE, capacity=BURST_RATE)


@limit(limiter)
def get_page(url: str) -> Response:
    return get(url)


@limit(limiter, consume=2)
async def do_stuff():
    await sleep(0.1)


def do_stuff():
    # do stuff
    
    with limit(limiter, consume=1.5):
        # do expensive stuff
        pass


async def do_stuff():
    # do stuff
    
    async with limit(limiter):
        # do expensive stuff
        pass
        

@limit(limiter, bucket=b'other stuff')
def do_other_stuff():
    pass
```