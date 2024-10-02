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

# Usage examples

- [Logging decorator](#logging-decorator)
- [Authorization decorator](#authorization-decorator)
- [Custom Response Header decorator](#custom-response-header-decorator)
- [Rate Limiting decorator](#rate-limiting-decorator)
- [Error Handling decorator](#error-handling-decorator)
- [Combining Multiple decorators](#combining-multiple-decorators)
- [Using `add_dependencies()` directly](#using-add_dependencies-directly)
- [Dependency injection with parameters](#dependency-injection-with-parameters)

## Logging decorator
Add a decorator to log incoming requests:

```python
from fastapi_decorators import add_dependencies
from fastapi import Request, Depends

def log_request():
    def dependency(request: Request):
        print(f"Received request: {request.method} {request.url}")
    return add_dependencies(Depends(dependency))

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
from fastapi_decorators import add_dependencies
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
    return add_dependencies(Depends(dependency))


@app.put("/users/{user_id}")
@authorize("users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
    ...

```

## Custom Response Header decorator
Create a decorator to add custom headers to responses:

```python
from fastapi_decorators import add_dependencies
from fastapi import Response, Depends

def add_custom_header(name: str, value: str):
    def dependency(response: Response):
        response.headers[name] = value
    return add_dependencies(Depends(dependency))

@app.get("/data")
@add_custom_header("X-Custom-Header", "MyValue")
def get_data():
    ...

```

## Rate Limiting decorator
Add rate limiting to your endpoints:

```python
from fastapi_decorators import add_dependencies
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
    return add_dependencies(Depends(dependency))

def get_ip_address(request: Request):
    return request.client.host

@app.get("/limited-endpoint")
@rate_limit(max_calls=5, period=60)
def limited_endpoint():
    ...

```

## Error Handling decorator
Create a decorator to handle exceptions and return custom responses:

```python
from fastapi_decorators import add_dependencies
from fastapi import Depends, Response
import traceback

def handle_errors():
    async def dependency(response: Response):
        try:
            yield
        except Exception as e:
            response.status_code = 500
            response.content = f"An error occurred: {str(e)}"

            # Optionally print the traceback
            traceback.print_exc()

    return add_dependencies(Depends(dependency))

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

## Using `add_dependencies()` directly
If you prefer, you can use add_dependencies directly without creating a custom decorator:

```python
from fastapi_decorators import add_dependencies
from fastapi import Depends, Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "expected-api-key":
        raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/secure-data")
@add_dependencies(Depends(verify_api_key))
def get_secure_data():
    ...

```

## Dependency injection with parameters
You can pass parameters to your dependencies through closures:

```python
from fastapi_decorators import add_dependencies
from fastapi import Depends, HTTPException

def verify_role(required_role: str):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Forbidden")
    return dependency

@app.get("/admin-area")
@add_dependencies(Depends(verify_role("admin")))
def admin_area():
    ...

```

# Credits
Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).
