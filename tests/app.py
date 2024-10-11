from functools import wraps
import logging
from time import sleep, time
from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fastapi_decorators import depends

logging.basicConfig(level=logging.INFO)


class UserUpdate(BaseModel):
    name: str
    email: str


class DataModel(BaseModel):
    value: int


rate_limit_store = {}
cache_storage = {}
error_log = []
fake_db = {
    "access_token": "valid_token",
    "users": {
        1: {"name": "John Doe", "email": "john@example.com"},
        2: {"name": "Jane Smith", "email": "jane@example.com"},
    },
    "items": [
        {"item_id": 1, "name": "Item One"},
        {"item_id": 2, "name": "Item Two"},
    ],
}


# Dependencies
def get_db() -> dict:
    return fake_db


def get_cache() -> dict:
    return cache_storage


def get_crash_log_storage() -> list:
    return error_log


def get_rate_limit_store() -> dict:
    return rate_limit_store


def get_current_user(
    token: str = Header(None),
    db: dict = Depends(get_db),
) -> str:
    if not token or token != db["access_token"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = "user_from_token"
    return user


def log_request(request: Request):
    logging.info(f"Request: {request.method} {request.url}")
    return request


def add_custom_header(response: Response):
    response.headers["X-Custom-Header"] = "CustomValue"
    return response


def get_request_id(request: Request) -> str:
    return request.client.host


# Decorators
def authorize(*required_scopes: str):
    async def dependency(
        token: str = Header(None),
        db: dict = Depends(get_db),
    ):
        if not token or token != db["access_token"]:
            raise HTTPException(status_code=401, detail="Unauthorized")

    return depends(Depends(dependency))


def custom_header():
    def dependency(response: Response):
        response.headers["X-Custom-Header"] = "CustomValue"
        return response

    return depends(Depends(dependency))


def log():
    async def dependency(request: Request):
        logging.info(f"Request: {request.method} {request.url}")
        return request

    return depends(Depends(dependency))


def rate_limit(max_calls: int, period: int):
    async def dependency(
        request_id: str = Depends(get_request_id),
        rate_limit_store: dict = Depends(get_rate_limit_store),
    ):
        calls_info = rate_limit_store.get(
            request_id, {"calls": 0, "last_reset": time()}
        )
        now = time()
        if now - calls_info["last_reset"] > period:
            # Reset rate limit
            calls_info = {"calls": 0, "last_reset": now}
        if calls_info["calls"] >= max_calls:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        calls_info["calls"] += 1
        rate_limit_store[request_id] = calls_info

    return depends(Depends(dependency))


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


def handle_errors():
    def decorator(func):
        @depends(crash_logs=Depends(get_crash_log_storage))
        @wraps(func)
        def wrapper(*args, crash_logs: list, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                crash_logs.append({"error": str(e), "function": func.__name__})
                return JSONResponse(status_code=500, content={"detail": str(e)})

        return wrapper

    return decorator


app = FastAPI()


@app.get("/items/")
@depends(Depends(get_db), Depends(log_request))
def read_items(db: dict = Depends(get_db)):
    """
    Endpoint to read items, using direct @depends() notation.
    """
    items = db["items"]
    return {"items": items}


@app.post("/items/")
@depends(Depends(add_custom_header))
def create_item(item: dict, response: Response, db: dict = Depends(get_db)):
    """
    Endpoint to create an item, adding a custom header to the response.
    """
    new_item = {"item_id": len(db["items"]) + 1, "name": item.get("name")}
    db["items"].append(new_item)
    return {"message": "Item created", "item": new_item}


@app.get("/users/me")
@log()
@authorize()
def read_current_user(current_user: str = Depends(get_current_user)):
    """
    Endpoint to read the current user, using custom decorators for logging and authorization.
    """
    return {"user": current_user}


@app.get("/reports/")
@log()
@custom_header()
def generate_report(response: Response):
    """
    Endpoint that generates a report, using custom decorators for logging and adding a header.
    """
    report = {"report": "This is your report"}
    return report


@app.put("/users/{user_id}")
@depends(Depends(get_db))
def update_user(user_id: int, user_data: UserUpdate, db: dict = Depends(get_db)):
    """
    Endpoint to update a user, using direct @depends() notation.
    """
    if user_id in db["users"]:
        db["users"][user_id].update(user_data.model_dump())
        return {"message": f"User {user_id} updated", "user": db["users"][user_id]}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.delete("/users/{user_id}")
@log()
@custom_header()
@authorize()
def delete_user(user_id: int, db: dict = Depends(get_db)):
    """
    Endpoint to delete a user, using custom decorators for logging, adding a header, and authorization.
    """
    if user_id in db["users"]:
        del db["users"][user_id]
        return {"message": f"User {user_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/limited-endpoint")
@rate_limit(max_calls=5, period=1)
def limited_endpoint():
    """
    Endpoint that is rate-limited.
    """
    return {"message": "You have accessed a rate-limited endpoint"}


@app.get("/expensive-operation")
@cache_response(max_age=1)
def expensive_operation():
    """
    Endpoint that is cached for 1 second.
    """
    sleep(1)
    return {"data": time()}


@app.get("/may-fail")
@handle_errors()
def may_fail_operation(should_fail: bool = False):
    """
    Endpoint that may raise exceptions.
    """
    if should_fail:
        raise ValueError("Simulated failure")
    return {"message": "Operation succeeded"}


@app.get("/error-log")
def get_error_log():
    return error_log
