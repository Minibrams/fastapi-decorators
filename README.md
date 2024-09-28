# FastAPI decorators

Small Python utility for wrapping your FastAPI endpoints in custom decorators.

## Installation
```bash
pip install fastapi-decorators
```

## Usage
Create a simple decorator that rejects unauthorized requests:

```python
from fastapi_decorators import add_dependencies

def authorize(*required_scopes: str):
    def decorator(func):
        def dependency(
            db_session: Session = Depends(get_db),
            ... # Your FastAPI dependencies here
        ):
            ... # Your auth logic here
        return add_dependencies(Depends(dependency))(func)
    return decorator


@app.put("/users/{user_id}")
@authorize("users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
    ...
```

# Credits
Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).
