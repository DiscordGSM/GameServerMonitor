import asyncio
from functools import partial, wraps
import sys

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

from typing import AsyncGenerator, Awaitable, Callable, List, TypeVar

R = TypeVar("R")
P = ParamSpec("P")


def run_in_executor(_func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @wraps(_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        func = partial(_func, *args, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(
            executor=None, func=func
        )

    return wrapper


T = TypeVar("T")


async def to_chunks(lst: List[T], n: int) -> AsyncGenerator[List[T], None]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        await asyncio.sleep(0)
        yield lst[i : i + n]


# Define a function to run the async function in a new event loop
def run_in_new_loop(async_func, *args):
    # Create a new event loop
    loop = asyncio.new_event_loop()
    # Set the new event loop as the event loop for the current context
    asyncio.set_event_loop(loop)
    try:
        # Run the async function in the new event loop
        loop.run_until_complete(async_func(*args))
    except RuntimeError:
        # RuntimeError('cannot schedule new futures after shutdown')
        pass
    except KeyboardInterrupt:
        # Optionally show a message or perform other cleanup here
        pass
    finally:
        # Close the loop after use
        loop.close()
