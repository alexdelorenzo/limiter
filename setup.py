from setuptools import setup
from pathlib import Path

requirements = Path('requirements.txt').read_text().split('\n')
readme = Path('README.md').read_text()


setup(name="limiter",
      version="0.1.2",
      description="⏲️ Rate-limiting, thread-safe and asynchronous decorators + context managers that implement the token-bucket algorithm.",
      long_description=readme,
      long_description_content_type="text/markdown",
      url="https://github.com/alexdelorenzo/limiter",
      author="Alex DeLorenzo",
      license="AGPL-3.0",
      packages=['limiter'],
      zip_safe=True,
      install_requires=requirements,
       keywords="rate-limit rate limit token bucket token-bucket token_bucket tokenbucket decorator contextmanager asynchronous threadsafe synchronous".split(' '),
     # entry_points={"console_scripts":
     #                   ["campfs = campfs.command:cmd"]},
      python_requires='~=3.7',
)
