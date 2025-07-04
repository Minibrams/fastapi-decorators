from functools import wraps
import logging
from time import sleep, time
from typing import Annotated, Any
from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fastapi_decorators import depends
from fastapi_decorators.types import F, Decorator

logging.basicConfig(level=logging.INFO)


class UserUpdate(BaseModel):
    name: str
    email: str


class DataModel(BaseModel):
    value: int


rate_limit_store: dict[str, Any] = {}
cache_storage: dict[str, Any] = {}
error_log: list[Any] = []
fake_db: dict[str, Any] = {
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
def get_db() -> dict[str, Any]:
    return fake_db


def get_cache() -> dict[str, Any]:
    return cache_storage


def get_crash_log_storage() -> list[Any]:
    return error_log


def get_rate_limit_store() -> dict[str, Any]:
    return rate_limit_store


def get_current_user(
    token: str = Header(None),
    db: dict[str, Any] = Depends(get_db),
) -> str:
    if not token or token != db["access_token"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = "user_from_token"
    return user


def log_request(request: Request) -> Request:
    logging.info(f"Request: {request.method} {request.url}")
    return request


def add_custom_header(response: Response) -> Response:
    response.headers["X-Custom-Header"] = "CustomValue"
    return response


def get_request_id(request: Request) -> str:
    if request.client is None:
        raise HTTPException(status_code=400, detail="Invalid request")

    return request.client.host


# Decorators
def authorize() -> Decorator:
    async def dependency(
        token: str = Header(None),
        db: dict[str, Any] = Depends(get_db),
    ) -> None:
        if not token or token != db["access_token"]:
            raise HTTPException(status_code=401, detail="Unauthorized")

    return depends(dependency)


def custom_header() -> Decorator:
    def dependency(response: Response) -> Response:
        response.headers["X-Custom-Header"] = "CustomValue"
        return response

    return depends(dependency)


def custom_header_func() -> Decorator:
    def dependency(response: Response) -> Response:
        response.headers["X-Custom-Header"] = "CustomValue"
        return response

    return depends(dependency)


@depends
def custom_header_shorthand(response: Response) -> Response:
    response.headers["X-Custom-Header"] = "CustomValue"
    return response


@depends
async def log(request: Request) -> Request:
    logging.info(f"Request: {request.method} {request.url}")
    return request


def rate_limit(max_calls: int, period: int) -> Decorator:
    async def dependency(
        request_id: str = Depends(get_request_id),
        rate_limit_store: dict[str, Any] = Depends(get_rate_limit_store),
    ) -> None:
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

    return depends(dependency)


def cache_response(max_age: int = 5) -> Decorator:
    def decorator(func: F) -> F:
        # Wrap the endpoint after adding the get_cache dependency
        @depends(cache=Depends(get_cache))
        @wraps(func)
        def wrapper(
            *args: Any,
            cache: dict[str, Any],
            **kwargs: Any,
        ) -> Any:
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


def handle_errors() -> Decorator:
    def decorator(func: F) -> F:
        @depends(crash_logs=Depends(get_crash_log_storage))
        @wraps(func)
        def wrapper(
            *args: Any,
            crash_logs: list[Any],
            **kwargs: Any,
        ) -> Any:
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
def read_items(db: dict[str, Any] = Depends(get_db)) -> dict[str, Any]:
    """
    Endpoint to read items, using direct @depends() notation.
    """
    items = db["items"]
    return {"items": items}


@app.post("/items/")
@depends(Depends(add_custom_header))
def create_item(
    item: dict[str, Any],
    db: dict[str, Any] = Depends(get_db),
) -> dict[str, Any]:
    """
    Endpoint to create an item, adding a custom header to the response.
    """
    new_item = {"item_id": len(db["items"]) + 1, "name": item.get("name")}
    db["items"].append(new_item)
    return {"message": "Item created", "item": new_item}


@app.get("/users/me")
@log
@authorize()
def read_current_user(current_user: str = Depends(get_current_user)) -> dict[str, Any]:
    """
    Endpoint to read the current user, using custom decorators for logging and authorization.
    """
    return {"user": current_user}


@app.get("/header-test-v1/")
@custom_header()
def header_test() -> dict[str, Any]:
    """
    Endpoint that generates a report, using custom decorators adding a header.
    """
    report = {"report": "This is your report"}
    return report


@app.get("/header-test-v2/")
@custom_header_func()
def header_test_func() -> dict[str, Any]:
    """
    Endpoint that generates a report, using custom decorators adding a header.
    The header is added with a function-only dependency.
    """
    report = {"report": "This is your report"}
    return report


@app.get("/header-test-v3/")
@custom_header_shorthand
def header_test_annotated() -> dict[str, Any]:
    """
    Endpoint that generates a report, using custom decorators adding a header.
    The header is added with a dependency created with the short-hand definition style.
    """
    report = {"report": "This is your report"}
    return report


@app.put("/users/{user_id}")
@depends(Depends(get_db))
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: dict[str, Any] = Depends(get_db),
) -> dict[str, Any]:
    """
    Endpoint to update a user, using direct @depends() notation.
    """
    if user_id in db["users"]:
        db["users"][user_id].update(
            user_data.model_dump()  # type: ignore
            if hasattr(user_data, "model_dump")
            else user_data.dict()
        )
        return {"message": f"User {user_id} updated", "user": db["users"][user_id]}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.delete("/users/{user_id}")
@log
@custom_header()
@authorize()
def delete_user(
    user_id: int,
    db: dict[str, Any] = Depends(get_db),
) -> dict[str, Any]:
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
def limited_endpoint() -> dict[str, Any]:
    """
    Endpoint that is rate-limited.
    """
    return {"message": "You have accessed a rate-limited endpoint"}


@app.get("/expensive-operation")
@cache_response(max_age=1)
def expensive_operation() -> dict[str, Any]:
    """
    Endpoint that is cached for 1 second.
    """
    sleep(1)
    return {"data": time()}


@app.get("/may-fail")
@handle_errors()
def may_fail_operation(should_fail: bool = False) -> dict[str, Any]:
    """
    Endpoint that may raise exceptions.
    """
    if should_fail:
        raise ValueError("Simulated failure")
    return {"message": "Operation succeeded"}


@app.get("/error-log")
def get_error_log() -> list[Any]:
    return error_log


@app.get("/headers")
@log
def expects_header(
    requestor_id: Annotated[str, Header(alias="requestor_id")],
) -> dict[str, str]:
    """
    Endpoint that returns current annotated requestor_id.
    """
    return {"requestor_id": requestor_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
