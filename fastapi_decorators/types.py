from typing import Any, Callable

F = Callable[..., Any]
Decorator = Callable[[F], F]
