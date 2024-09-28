import asyncio
from collections import OrderedDict
from functools import wraps
from inspect import Parameter, signature
from typing import Callable


def add_dependencies(*dependencies):
    """
    Adds dependencies to be executed, but not provided as function arguments to the underlying function

    E.g.:
    ```python
    @app.put("/users/{user_id}")
    @add_dependencies(Depends(get_admin_roles))
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```

    Can also be used to construct custom decorators that define their own dependencies:
    ```python
    def authorize(*required_scopes: str):
        def decorator(func):
            def dependency(
                x_auth_token: str = Header(None),
                db_session: Session = Depends(get_db),
            ):
                # Execute your authorization logic here
                ...
            return add_dependencies(Depends(dependency))(func)
        return decorator
    ```

    The `authorize` decorator can now be used to require specific scopes for a route:

    ```python
    @app.put("/users/{user_id}")
    @authorize("users:write")
    def update_user(*, user_id: int, user_update: UserUpdate):
        ...
    ```
    """

    def decorator(func: Callable):
        sig = signature(func)
        original_parameters = sig.parameters
        new_parameters = OrderedDict(original_parameters)

        for i, dependency in enumerate(dependencies):
            name = _get_anonymous_dependency_name(i, new_parameters)
            new_parameters[name] = Parameter(
                name, kind=Parameter.KEYWORD_ONLY, default=dependency
            )

        is_coroutine = asyncio.iscoroutinefunction(func)
        if is_coroutine:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                kwargs = {k: v for k, v in kwargs.items() if k in original_parameters}
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                kwargs = {k: v for k, v in kwargs.items() if k in original_parameters}
                return func(*args, **kwargs)

        wrapper.__signature__ = sig.replace(parameters=tuple(new_parameters.values()))
        return wrapper
    return decorator


def _get_anonymous_dependency_name(index: int, current_parameters: OrderedDict):
    name = f"__unnamed_dependency_{index}"
    while name in current_parameters.keys():
        index += 1
        name = f"__unnamed_dependency_{index}"
    return name
