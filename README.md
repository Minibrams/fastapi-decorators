# FastAPI decorators
![CI](https://github.com/Minibrams/fastapi-decorators/actions/workflows/ci.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)
[![Downloads](https://img.shields.io/pypi/dm/fastapi-decorators.svg)](https://pypi.org/project/fastapi-decorators/)

Create decorators that leverage FastAPI's `Depends()` and built-in dependencies, enabling you to inject dependencies directly into your decorators.

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

It can even be used to overwrite the endpoint logic while *still* using dependencies:

```python
def cached():
    def decorator(func):
        @depends(cache=Depends(get_cache))
        @wraps(func)
        def wrapper(*args, cache, **kwargs):
            
            # Check if we have a cached response
            if cache.hit():
                return cache.get()

            # Cache miss - call the endpoint as usual
            result = func(*args, **kwargs)

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
