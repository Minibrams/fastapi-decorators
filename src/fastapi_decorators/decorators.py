from __future__ import annotations

import asyncio
from collections import OrderedDict
from functools import wraps
from inspect import Parameter, Signature, signature
from typing import Any, Callable, Dict, Tuple


def add_dependencies(*dependencies: Any) -> Callable:
    """
    Decorator to add dependencies to a function without exposing them as arguments.

    This is particularly useful in frameworks like FastAPI, where dependencies can be injected.

    **Usage Example:**

    ```python
    @app.put("/users/{user_id}")
    @add_dependencies(Depends(get_admin_roles))
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```

    **Custom Decorator Example:**

    ```python
    def authorize(*required_scopes: str):
        def decorator(func: Callable):
            async def dependency(
                x_auth_token: str = Header(None),
                db_session: Session = Depends(get_db),
            ):
                # Authorization logic here
                ...
            return add_dependencies(Depends(dependency))(func)
        return decorator
    ```

    **Using the Custom Decorator:**

    ```python
    @app.put("/users/{user_id}")
    @authorize("users:write")
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```
    """

    def decorator(func: Callable) -> Callable:
        sig: Signature = signature(func)
        original_parameters = sig.parameters
        new_parameters = OrderedDict(original_parameters)

        for i, dependency in enumerate(dependencies):
            name = _generate_dependency_name(i, new_parameters)
            new_parameters[name] = Parameter(
                name,
                kind=Parameter.KEYWORD_ONLY,
                default=dependency,
                annotation=Any,
            )

        @wraps(func)
        async def async_wrapper(*args: Tuple[Any], **kwargs: Dict[str, Any]) -> Any:
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k in original_parameters
            }
            return await func(*args, **filtered_kwargs)

        @wraps(func)
        def sync_wrapper(*args: Tuple[Any], **kwargs: Dict[str, Any]) -> Any:
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k in original_parameters
            }
            return func(*args, **filtered_kwargs)

        wrapper = (
            async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        )
        wrapper.__signature__ = sig.replace(parameters=tuple(new_parameters.values()))  # type: ignore
        return wrapper

    return decorator


def _generate_dependency_name(
    index: int, current_parameters: Dict[str, Parameter]
) -> str:
    """Generates a unique name for an anonymous dependency."""
    base_name = f"__dependency_{index}"
    name = base_name
    while name in current_parameters:
        index += 1
        name = f"{base_name}_{index}"
    return name
