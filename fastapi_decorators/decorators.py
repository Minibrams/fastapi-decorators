from __future__ import annotations

import asyncio
from functools import wraps
from inspect import Parameter, signature, unwrap
from types import MappingProxyType
from typing import Any, Tuple, Union, get_type_hints

from fastapi import Depends, params


from .types import Decorator, F


def depends(*args: Any, **kwargs: Any) -> Decorator:
    """
    Decorator to add FastAPI dependencies to a function without exposing them as arguments.

    The @depends decorator ensures that the decorated function is registered as a FastAPI dependency.
    As such, the two following examples are equivalent:

    ```python
    @depends(Depends(authenticate_user))
    @depends(authenticate_user)
    ```

    **Usage Example:**

    ```python
    @app.put("/users/{user_id}")
    @depends(Depends(get_admin_roles))
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```

    **Custom Decorator Example:**

    ```python
    def authorize(*required_scopes: str):
        async def dependency(
            x_auth_token: str = Header(None),
            db_session: Session = Depends(get_db),
        ):
            # Authorization logic here
            ...
        return depends(Depends(dependency))
    ```

    **Using the Custom Decorator:**

    ```python
    @app.put("/users/{user_id}")
    @authorize("users:write")
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```
    """

    def decorator(func: F) -> F:
        original_func = unwrap(func)
        original_signature = signature(func, follow_wrapped=True)

        hints = get_type_hints(
            original_func,
            globalns=original_func.__globals__,
            localns=None,
            include_extras=True,
        )

        resolved_params: dict[str, Parameter] = {}
        for name, param in original_signature.parameters.items():
            anno = hints.get(name, param.annotation)
            resolved_params[name] = param.replace(annotation=anno)

        dep_params = _add_dependency_parameters(
            args,
            kwargs,
            MappingProxyType(resolved_params),
        )

        all_params = {**resolved_params, **dep_params}

        new_signature = original_signature.replace(
            parameters=tuple(all_params.values()),
            return_annotation=hints.get("return", original_signature.return_annotation),
        )

        wrapper = _create_wrapper(func, all_params)
        wrapper.__signature__ = new_signature  # type: ignore

        return wrapper

    return decorator


def _add_dependency_parameters(
    dependencies: Tuple[Any, ...],
    named_dependencies: dict[str, Any],
    original_parameters: MappingProxyType[str, Parameter],
) -> dict[str, Parameter]:
    """
    Adds dependency parameters to the function's parameters.

    Args:
        dependencies: A tuple of dependency objects.
        original_parameters: A mapping of the original function's parameter names to Parameters.

    Returns:
        A new dictionary of parameters including the dependencies.
    """
    new_parameters = dict(original_parameters)
    for i, dependency in enumerate(dependencies):
        name = _generate_dependency_name(i, new_parameters)
        new_parameters[name] = Parameter(
            name,
            kind=Parameter.KEYWORD_ONLY,
            default=_ensure_dependency(dependency),
            annotation=Any,
        )

    for name, dependency in named_dependencies.items():
        new_parameters[name] = Parameter(
            name,
            kind=Parameter.KEYWORD_ONLY,
            default=_ensure_dependency(dependency),
            annotation=Any,
        )

    return new_parameters


def _generate_dependency_name(
    index: int,
    current_parameters: dict[str, Parameter],
) -> str:
    """
    Generates a unique name for an anonymous dependency.

    Args:
        index: The initial index for naming.
        current_parameters: Existing parameters to avoid naming conflicts.

    Returns:
        A unique parameter name as a string.
    """
    base_name = f"__dependency_{index}"
    name = base_name
    while name in current_parameters:
        index += 1
        name = f"{base_name}_{index}"

    return name


def _create_wrapper(
    func: F,
    original_parameters: dict[str, Parameter],
) -> F:
    """
    Creates a wrapper function that filters out dependency arguments.

    Args:
        func: The original function to wrap.
        original_parameters: A mapping of the original function's parameter names to Parameters.

    Returns:
        A wrapper function that excludes dependency arguments when calling the original function.
    """
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in original_parameters and not k.startswith("__dependency_")
            }
            return await func(*args, **filtered_kwargs)

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in original_parameters and not k.startswith("__dependency_")
            }
            return func(*args, **filtered_kwargs)

        return sync_wrapper


def _ensure_dependency(func: Union[F, params.Depends]) -> Union[params.Depends, Any]:
    """
    Ensures that a dependency is registered as a FastAPI dependency.
    """
    if not isinstance(func, params.Depends):
        return Depends(func)

    return func
