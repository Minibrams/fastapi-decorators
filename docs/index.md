# Introduction

Create decorators that leverage FastAPI's `Depends()` and built-in dependencies, enabling you to inject dependencies directly into your decorators.

## Installation
```bash
uv add fastapi-decorators

# or

pip install fastapi-decorators
```

## TL;DR
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

## Usage examples

### Using `depends()` directly
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

### Logging decorator
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

### Authorization decorator
Create a simple decorator that rejects unauthorized requests:

!!! note

    The API docs will reflect the authentication requirement for this endpoint
    because of the added OAuth2 dependency.


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

### Custom Response Header decorator
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

### Rate Limiting decorator
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

### Caching decorator
Add caching to your endpoints:

```python linenums="1" hl_lines="10 12"
cache_storage = {}

def get_cache() -> dict:
    return cache_storage  # Use a real cache like Redis or Memcached

def cache_response(max_age: int = 5):
    def decorator(func):

        # Wrap the endpoint after adding the get_cache dependency
        @depends(cache=Depends(get_cache)) # (1)!
        @wraps(func)
        def wrapper(*args, cache: dict, **kwargs): # (2)!
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


### Error Handling decorator
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

### Combining Multiple decorators
You can combine multiple decorators to compose complex behavior:

```python
@app.post("/submit")
@log_request()
@add_custom_header("X-Processed-By", "FastAPI")
@handle_errors()
def submit_data(data: DataModel):
    ...

```

### Dependency injection with parameters
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

## Credits
Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).
