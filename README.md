# FastAPI decorators
![CI](https://github.com/Minibrams/fastapi-decorators/actions/workflows/ci.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)
[![Downloads](https://img.shields.io/pypi/dm/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)

Create decorators with a `@depends()` decorator that leverages FastAPI's `Depends()` and built-in dependencies.

# Installation
```bash
pip install fastapi-decorators
```

# TL;DR
The library supplies the `depends()` decorator function which allows you to decorate your FastAPI endpoints with dependencies.


```python
from fastapi_decorators import depends

@app.get("/items/{item_id}")
@depends(Depends(get_current_user))
def read_item(item_id: int):
    ...
```

You can use it to make declarative decorators like so:
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def authorize(*required_scopes: str):
    def dependency(token: str = Depends(oauth2_scheme)):
        # Your auth logic here
        raise HTTPException(status_code=401, detail="Unauthorized")
    return depends(Depends(dependency))


@app.put("/users/{user_id}")
@authorize("users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
```

It can even be used to overwrite the endpoint logic while *still* using dependencies:

```python
def cached():
    def decorator(func):
        @depends(cache=Depends(get_cache))    # Note: Dependency `cache` registered here
        @wraps(func)
        def wrapper(*args, cache, **kwargs):  # Note: Dependency `cache` accessible here
            if cache.hit():
                return cache.get()

            result = func(*args, **kwargs)    # Note: Execute the underlying endpoint function as normal

            cache.set(result)
            return result
        return wrapper
    return decorator

@app.get("/very-expensive-operation")
@cached()
def get_a_very_expensive_resource():
    ...
```

# Documentation
See the documentation [here](https://fastapi-decorators.pages.dev/).
