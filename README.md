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
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", 
    auto_error=False,
)

def authorize(*required_scopes: str):
    def decorator(func):
        def dependency(
            token: Optional[str] = Depends(oauth2_password_scheme),
            db_session: Session = Depends(get_db),
        ):
            # Execute your auth logic here
            ...
        return add_dependencies(Depends(dependency))(func)
    return decorator
```

The decorator can be used like so:
```python
@app.put("/users/{user_id}")
@authorize("users:write")
def update_user(*, user_id: int, user_update: UserUpdate):
    ...
```

# Credits
Inspired by solutions suggested by [@gocreating](https://github.com/gocreating) and [@dmontagu](https://github.com/dmontagu).