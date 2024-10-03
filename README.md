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
The library supplies the `depends()` decorator function which effectively allows you to add argument dependencies to your FastAPI endpoints.

For example, the following three endpoints have the same signature:
```python
# Using normal dependencies
@app.get("/items/{item_id}")
def read_item(item_id: int, _ = Depends(get_current_user)):
    ...

# Using @depends() directly
@app.get("/items/{item_id}")
@depends(Depends(get_current_user))
def read_item(item_id: int):
    ...

# Using a custom decorator
def authorize():
    def dependency(user = Depends(get_current_user)):
        return user
    return depends(Depends(dependency))

@app.get("/items/{item_id}")
@authorize()
def read_item(item_id: int):
    ...
```

# Usage examples

- [Using `depends()` directly](#using-depends-directly)
- [Logging decorator](#logging-decorator)
- [Authorization decorator](#authorization-decorator)
- [Custom Response Header decorator](#custom-response-header-decorator)
- [Rate Limiting decorator](#rate-limiting-decorator)
- [Caching decorator](#caching-decorator)
- [Error Handling decorator](#error-handling-decorator)
- [Combining Multiple decorators](#combining-multiple-decorators)
- [Dependency injection with parameters](#dependency-injection-with-parameters)

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

## Logging decorator
Add a decorator to log incoming requests:

```python
from fastapi_decorators import depends
from fastapi import Request, Depends

def log_request():
    def dependency(request: Request):
        print(f"Received request: {request.method} {request.url}")
    return depends(Depends(dependency))

@app.get("/items/{item_id}")
@log_request()
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def authorize(*required_scopes: str):
    def dependency(token: str = Depends(oauth2_scheme)):
        # Your auth logic here
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Check scopes and permissions
        pass
    return depends(Depends(dependency))


@app.put("/users/{user_id}")
@authorize("users:write")
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
    return depends(Depends(dependency))

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
    return depends(Depends(dependency))

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
        @depends(cache=Depends(get_cache))
        @wraps(func)
        def wrapper(*args, cache: dict, **kwargs):
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
@depends(Depends(verify_role("admin")))
def admin_area():
    ...

```

# Credits
Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).
