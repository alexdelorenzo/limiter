# ⏲️ Easy rate limiting for Python

`limiter` makes it easy to add [rate limiting](https://en.wikipedia.org/wiki/Rate_limiting) to Python projects, using
a [token bucket](https://en.wikipedia.org/wiki/Token_bucket) algorithm. `limiter` can provide Python projects and
scripts with:

- Rate limiting thread-safe [decorators](https://www.python.org/dev/peps/pep-0318/)
- Rate limiting async decorators
- Rate limiting thread-safe [context managers](https://www.python.org/dev/peps/pep-0343/)
- Rate
  limiting [async context managers](https://www.python.org/dev/peps/pep-0492/#asynchronous-context-managers-and-async-with)

Here are some features and benefits of using `limiter`:

- Easily control burst and average request rates
- It
  is [thread-safe, with no need for a timer thread](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm#Comparison_with_the_token_bucket)
- It adds [jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) to help with contention
- It has a simple API that takes advantage of Python's features, idioms
  and [type hinting](https://www.python.org/dev/peps/pep-0483/)

## Example

Here's an example of using a limiter as a decorator and context manager:

```python
from aiohttp import ClientSession
from limiter import Limiter


limit_downloads = Limiter(rate=2, capacity=5, consume=2)


@limit_downloads
async def download_image(url: str) -> bytes:
  async with ClientSession() as session, session.get(url) as response:
    return await response.read()


async def download_page(url: str) -> str:
  async with (
    ClientSession() as session,
    limit_downloads,
    session.get(url) as response
  ):
    return await response.text()
```

## Usage

You can define limiters and use them dynamically across your project.

**Note**: If you're using Python version `3.9.x` or below, check
out [the documentation for version `0.2.0` of `limiter` here](https://github.com/alexdelorenzo/limiter/blob/master/README-0.2.0.md).

### `Limiter` instances

`Limiter` instances take `rate`, `capacity` and `consume` arguments.

- `rate` is the token replenishment rate per second. Tokens are automatically added every second.

- `consume` is the amount of tokens consumed from the token bucket upon successfully taking tokens from the bucket.

- `capacity` is the total amount of tokens the token bucket can hold. Token replenishment stops when this capacity is
  reached.

### Limiting blocks of code

`limiter` can rate limit all Python callables, and limiters can be used as context managers.

You can define a limiter with a set refresh `rate` and total token `capacity`. You can set the amount of tokens to
consume dynamically with `consume`, and the `bucket` parameter sets the bucket to consume tokens from:

```python3
from limiter import Limiter


REFRESH_RATE: int = 2
BURST_RATE: int = 3
MSG_BUCKET: str = 'messages'

limiter: Limiter = Limiter(rate=REFRESH_RATE, capacity=BURST_RATE)
limit_msgs: Limiter = limiter(bucket=MSG_BUCKET)


@limiter
def download_page(url: str) -> bytes:
  ...


@limiter(consume=2)
async def download_page(url: str) -> bytes:
  ...


def send_page(page: bytes):
  with limiter(consume=1.5, bucket=MSG_BUCKET):
    ...


async def send_page(page: bytes):
  async with limit_msgs:
    ...


@limit_msgs(consume=3)
def send_email(to: str):
  ...


async def send_email(to: str):
  async with limiter(bucket=MSG_BUCKET):
    ...
```

In the example above, both `limiter` and `limit_msgs` share the same limiter. The only difference is that `limit_msgs`
will take tokens from the `MSG_BUCKET` bucket by default.

```python3
assert limiter.limiter is limit_msgs.limiter
assert limiter.bucket != limit_msgs.bucket
assert limiter != limit_msgs
```

### Creating new limiters

You can reuse existing limiters in your code, and you can create new limiters from the parameters of an existing limiter
using the `new()` method.

Or, you can define a new limiter entirely:

```python
# you can reuse existing limiters
limit_downloads: Limiter = limiter(consume=2)

# you can use the settings from an existing limiter in a new limiter
limit_downloads: Limiter = limiter.new(consume=2)

# or you can simply define a new limiter
limit_downloads: Limiter = Limiter(REFRESH_RATE, BURST_RATE, consume=2)


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

Let's look at the difference between reusing an existing limiter, and creating new limiters with the `new()` method:

```python3
limiter_a: Limiter = limiter(consume=2)
limiter_b: Limiter = limiter.new(consume=2)
limiter_c: Limiter = Limiter(REFRESH_RATE, BURST_RATE, consume=2)

assert limiter_a != limiter
assert limiter_a != limiter_b != limiter_c

assert limiter_a != limiter_b
assert limiter_a.limiter is limiter.limiter
assert limiter_a.limiter is not limiter_b.limiter

assert limiter_a.attrs == limiter_b.attrs == limiter_c.attrs
```

The only things that are equivalent between the three new limiters above are the limiters' attributes, like
the `rate`, `capacity`, and `consume` attributes.

### Creating anonymous, or single-use, limiters

You don't have to assign `Limiter` objects to variables. Anonymous limiters don't share a token bucket like named
limiters can. They work well when you don't have a reason to share a limiter between two or more blocks of code, and
when a limiter has a single or independent purpose.

`limiter`, after version `v0.3.0`, ships with a `limit` type alias for `Limiter`:

```python3
from limiter import limit


@limit(capacity=2, consume=2)
async def send_message():
  ...


async def upload_image():
  async with limit(capacity=3) as limiter:
    ...
```

The above is equivalent to the below:

```python3
from limiter import Limiter


@Limiter(capacity=2, consume=2)
async def send_message():
  ...


async def upload_image():
  async with Limiter(capacity=3) as limiter:
    ...
```

Both `limit` and `Limiter` are the same object:

```python3
assert limit is Limiter
```

### Jitter

A `Limiter`'s `jitter` argument adds jitter to help with contention.

The value is in milliseconds, and can be any of these:

- `False`, to add no jitter. This is the default.
- `True`, to add a random amount of jitter.
- A number, to add a fixed amount of jitter.
- A `range` object, to add a random amount of jitter within the range.
- A `tuple` of two numbers, `start` and `stop`, to add a random amount of jitter between the two numbers.
- A `tuple` of three numbers: `start`, `stop` and `step`, to add jitter like you would with `range`.

For example, if you want to use a random amount of jitter between `0` and `100` milliseconds:

```python3
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=(0, 100))
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=(0, 100, 1))
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=range(0, 100))
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=range(0, 100, 1))
```

All of the above are equivalent to each other.

You can also supply values for `jitter` when using decorators or context-managers:

```python3
limiter = Limiter(rate=2, capacity=5, consume=2)


@limiter(jitter=range(0, 100))
def download_page(url: str) -> bytes:
  ...


async def download_page(url: str) -> bytes:
    async with limiter(jitter=(0, 100)):
        ...
```

You can use the above to override default values of `jitter` in a `Limiter` instance.


To add a small amount of random jitter, supply `True`  as the value:
```python3
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=True)

# or

@limiter(jitter=True)
def download_page(url: str) -> bytes:
  ...
```

To turn off jitter in a `Limiter` configured with jitter, you can supply `False` as the value:

```python3
limiter = Limiter(rate=2, capacity=5, consume=2, jitter=range(10))


@limiter(jitter=False)
def download_page(url: str) -> bytes:
  ...


async def download_page(url: str) -> bytes:
    async with limiter(jitter=False):
        ...
```

Or create yourself a new limiter with jitter turned off:

```python3
limiter: Limiter = limiter.new(jitter=False)
```

## Installation

### Requirements

- Python 3.10+ for versions `0.3.0` and up
- [Python 3.7+ for versions below `0.3.0`](https://github.com/alexdelorenzo/limiter/blob/master/README-0.2.0.md)

### Install via PyPI

```bash
$ python3 -m pip install limiter
```

## License

See [`LICENSE`](/LICENSE). If you'd like to use this project with a different license, please get in touch.
