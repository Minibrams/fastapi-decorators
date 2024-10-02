from __future__ import annotations

import asyncio
from functools import wraps
from inspect import Parameter, signature
from typing import Any, Callable, Dict, Tuple, TypeVar, cast

F = TypeVar('F', bound=Callable[..., Any])

def add_dependencies(*dependencies: Any) -> Callable[[F], F]:
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
        async def dependency(
            x_auth_token: str = Header(None),
            db_session: Session = Depends(get_db),
        ):
            # Authorization logic here
            ...
        return add_dependencies(Depends(dependency))(func)
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
        original_signature = signature(func)
        original_parameters = original_signature.parameters

        new_parameters = _add_dependency_parameters(dependencies, original_parameters)
        new_signature = original_signature.replace(parameters=tuple(new_parameters.values()))
        
        wrapper = _create_wrapper(func, original_parameters)
        wrapper.__signature__ = new_signature  # type: ignore

        return cast(F, wrapper)

    return decorator

def _add_dependency_parameters(
    dependencies: Tuple[Any, ...],
    original_parameters: Dict[str, Parameter],
) -> Dict[str, Parameter]:
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
            default=dependency,
            annotation=Any,
        )

    return new_parameters


def _generate_dependency_name(
    index: int, 
    current_parameters: Dict[str, Parameter],
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
    func: Callable, 
    original_parameters: Dict[str, Parameter],
) -> Callable:
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
                k: v for k, v in kwargs.items() if k in original_parameters
            }
            return await func(*args, **filtered_kwargs)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k in original_parameters
            }
            return func(*args, **filtered_kwargs)
        return sync_wrapper
