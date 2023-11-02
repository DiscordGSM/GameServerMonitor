import asyncio
from functools import partial, wraps
import sys

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

from typing import Awaitable, Callable, Generator, List, TypeVar

R = TypeVar("R")
P = ParamSpec("P")


def run_in_executor(_func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @wraps(_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        func = partial(_func, *args, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(executor=None, func=func)

    return wrapper


T = TypeVar('T')


async def to_chunks(lst: List[T], n: int) -> Generator[List[T], None, None]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        await asyncio.sleep(0)
        yield lst[i:i + n]
