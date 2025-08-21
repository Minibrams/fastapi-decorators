# FastAPI decorators <!-- omit in toc -->

![CI](https://github.com/Minibrams/fastapi-decorators/actions/workflows/ci.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/fastapi-decorators?style=plastic&color=2334D058.svg)](https://pypi.org/project/fastapi-decorators/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-decorators?style=plastic&color=2334D058.svg)](https://pypi.org/project/fastapi-decorators/)

Create decorators with a `@depends()` decorator that leverages FastAPI's `Depends()` and built-in dependencies.

# Installation <!-- omit in toc -->

```bash
uv add fastapi-decorators

# or

pip install fastapi-decorators
```

# TL;DR <!-- omit in toc -->

The library supplies the `depends()` decorator function which converts any function to a decorator that resolves FastAPI dependencies.

Create dependency-enabled decorators simply by using `@depends`:

```python
from fastapi_decorators import depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

@depends
def authenticate(token: str | None = Depends(oauth2_scheme)):
    if token is None:
        raise HTTPException(status_code=401, detail="Unauthenticated")

@app.get("/items/{item_id}")
@authenticate
def read_item(item_id: int):
    ...
```

You can use it to make decorator factories like so:

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def authorize(scope: str):
    @depends
    def dependency(token: str = Depends(oauth2_scheme)):
        jwt = decode_jwt(token)
        if scope not in jwt.scopes:
            raise HTTPException(status_code=403, detail="Unauthorized")

    return dependency

@app.put("/users/{user_id}")
@authorize("users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
```

It can even be used to overwrite the endpoint logic while _still_ using dependencies:

```python
def cached():
    def decorator(func):
        @depends(cache=Depends(get_cache))    # Dependency `cache` registered here
        @wraps(func)
        def wrapper(*args, cache, **kwargs):  # Dependency `cache` accessible here
            if cache.hit():
                return cache.get()

            result = func(*args, **kwargs)    # Execute the underlying endpoint function as normal

            cache.set(result)
            return result
        return wrapper
    return decorator

@app.get("/very-expensive-operation")
@cached()
def get_a_very_expensive_resource():
    ...
```

# Usage examples

A more detailed version of the documentation is available [here](https://fastapi-decorators.abrams.dk/).

- [Usage examples](#usage-examples)
  - [Using `depends()` directly](#using-depends-directly)
  - [Simple decorator](#simple-decorator)
  - [Decorator factory](#decorator-factory)
  - [Logging decorator](#logging-decorator)
  - [Authorization decorator](#authorization-decorator)
  - [Custom Response Header decorator](#custom-response-header-decorator)
  - [Rate Limiting decorator](#rate-limiting-decorator)
  - [Caching decorator](#caching-decorator)
  - [Error Handling decorator](#error-handling-decorator)
  - [Combining Multiple decorators](#combining-multiple-decorators)
  - [Dependency injection with parameters](#dependency-injection-with-parameters)
  - [Satisfying type checkers](#satisfying-type-checkers)
- [Credits](#credits)

## Using `depends()` directly

If you prefer, you can use depends directly without creating a custom decorator:

```python
from fastapi_decorators import depends
from fastapi import Depends, Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "expected-api-key":
        raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/secure-data")
@depends(Depends(verify_api_key))
def get_secure_data():
    ...

```

## Simple decorator

The simplest way to create a decorator is to simply convert a function into a dependency decorator with `@depends`:

```python
from fastapi_decorators import depends
from fastapi import Request, Depends

@depends
def audit_request(request: Request, db: Session = Depends(get_db)):
    log = AuditLog(request.host.ip, request.url.path)
    db.add(log)
    db.commit()

@app.get('/users/')
@audit_request
def get_users():
    ...
```

If preferred, the non-decorator syntax can also be used:

```python
from fastapi_decorators import depends
from fastapi import Request, Depends


def audit_request():
    def dependency(request: Request, db: Session = Depends(get_db)):
        log = AuditLog(request.host.ip, request.url.path)
        db.add(log)
        db.commit()

    return depends(dependency)

@app.get('/users/')
@audit_request()
def get_users():
    ...
```

## Decorator factory

In some cases, you need to provide variations of the same dependency.
To do this, create a decorator factory:

```python
def require_headers(*headers: str):
    def dependency(request: Request):
        if not all(header in request.headers for header in headers):
            raise HTTPException(status=400, detail="Required headers not provided.")

    return depends(dependency)


@app.put("/users/{user_id}")
@require_headers("X-API-KEY", "X-TENANT-ID")
def update_user(*, user_id: int, user_update: UserUpdate):
    ...
```

## Logging decorator

Add a decorator to log incoming requests:

```python
from fastapi_decorators import depends
from fastapi import Request

@depends
def log_request(request: Request):
    print(f"Received request: {request.method} {request.url}")

@app.get("/items/{item_id}")
@log_request
def read_item(item_id: int):
    ...

```

## Authorization decorator

Create a simple decorator that rejects unauthorized requests:

> The API docs will reflect the authentication requirement for this endpoint
> because of the added OAuth2 dependency.

```python
from fastapi_decorators import depends
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def authorize(*scopes: str):
    def dependency(token: str | None = Depends(oauth2_scheme)):
        if not token:
            raise HTTPException(status_code=401, detail="Unauthenticated")

        if not all(scope in token.scopes for scope in scopes):
            raise HTTPException(status_code=403, detail="Unauthorized")

    return depends(dependency)


@app.put("/users/{user_id}")
@authorize("users:read", "users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
    ...

```

## Custom Response Header decorator

Create a decorator to add custom headers to responses:

```python
from fastapi_decorators import depends
from fastapi import Response, Depends

def add_custom_header(name: str, value: str):
    def dependency(response: Response):
        response.headers[name] = value
    return depends(dependency)

@app.get("/data")
@add_custom_header("X-Custom-Header", "MyValue")
def get_data():
    ...

```

## Rate Limiting decorator

Add rate limiting to your endpoints:

```python
from fastapi_decorators import depends
from fastapi import Depends, HTTPException, Request
from time import time

rate_limit_store = {}

def rate_limit(max_calls: int, period: int):
    def dependency(ip_address: str = Depends(get_ip_address)):
        # Simple rate limiting logic
        now = time()
        calls, last_reset = rate_limit_store.get(ip_address, (0, now))
        if now - last_reset > period:
            # Reset rate limit
            calls = 0
            last_reset = now
        if calls >= max_calls:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        calls += 1
        rate_limit_store[ip_address] = (calls, last_reset)
    return depends(dependency)

def get_ip_address(request: Request):
    return request.client.host

@app.get("/limited-endpoint")
@rate_limit(max_calls=5, period=60)
def limited_endpoint():
    ...

```

## Caching decorator

Add caching to your endpoints:

```python
cache_storage = {}

def get_cache() -> dict:
    return cache_storage  # Use a real cache like Redis or Memcached

def cache_response(max_age: int = 5):
    def decorator(func):

        # Wrap the endpoint after adding the get_cache dependency
        @depends(cache=Depends(get_cache)) # The `cache` dependency is defined here
        @wraps(func)
        def wrapper(*args, cache: dict, **kwargs): # The `cache` dependency can be accessed here
            key = func.__name__

            if key in cache:
                timestamp, data = cache[key]
                if time() - timestamp < max_age:
                    # Cache hit
                    return data

            # Cache miss - call the endpoint as usual
            result = func(*args, **kwargs)

            # Store the result in the cache
            cache[key] = time(), result
            return result

        return wrapper
    return decorator

@app.get("/cached-data")
@cache_response(max_age=10)
def get_cached_data():
    ...
```

1. We add the `get_cache` dependency with a keyword argument so we can access it in the wrapper function later.
2. Because we added the `get_cache` dependency with the keyword argument `cache`, we can access it in here. This also works for normal endpoints.

## Error Handling decorator

Create a decorator to handle exceptions and return custom responses:

```python
from fastapi_decorators import depends
from fastapi import Depends, Response

crash_logs = []

def get_crash_log_storage() -> list:
    return crash_logs  # Use a real storage like a database

def handle_errors():
    def decorator(func):

        # Wrap the endpoint after adding the crash_logs dependency
        @depends(crash_logs = Depends(get_crash_log_storage))
        @wraps(func)
        def wrapper(*args, crash_logs: list, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error and return a custom response
                crash_logs.append({ 'error': str(e), 'function': func.__name__ })
                return JSONResponse(status_code=500, content={ "detail": str(e) })

        return wrapper
    return decorator

@app.get("/may-fail")
@handle_errors()
def may_fail_operation():
    ...

```

## Combining Multiple decorators

You can combine multiple decorators to compose complex behavior:

```python
@app.post("/submit")
@log_request()
@add_custom_header("X-Processed-By", "FastAPI")
@handle_errors()
def submit_data(data: DataModel):
    ...

```

## Dependency injection with parameters

You can pass parameters to your dependencies through closures:

```python
from fastapi_decorators import depends
from fastapi import Depends, HTTPException

def verify_role(required_role: str):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Forbidden")
    return dependency

@app.get("/admin-area")
@depends(verify_role("admin"))
def admin_area():
    ...

```

## Satisfying type checkers

If you're using a type checker like Mypy with a `strict` configuration, the library exposes two useful types `Decorator` and `F` for satisfying type checks on decorators and their decorated functions:

```python
from fastapi_decorators import depends
from fastapi_decorators.types import Decorator, F

def authorize() -> Decorator:
    async def dependency(...) -> None:
        ...

    return depends(dependency)

def cache_response(...) -> Decorator:
    def decorator(func: F) -> F:

        @depends(cache=Depends(get_cache))
        @wraps(func)
        def wrapper(...) -> Any:
            ...

        return wrapper
    return decorator
```

# Credits

Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).
