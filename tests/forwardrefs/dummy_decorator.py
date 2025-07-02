from functools import wraps
from typing import Any

from fastapi import Depends

from fastapi_decorators import depends
from fastapi_decorators.types import F


def get_nothing() -> None:
    return None


def empty_decorator(func: F) -> F:
    @depends(test=Depends(get_nothing))
    @wraps(func)
    def wrapper(
        *args: Any,
        test: None,
        **kwargs: Any,
    ) -> Any:
        # Don't do anything
        result = func(*args, **kwargs)
        return result

    return wrapper
