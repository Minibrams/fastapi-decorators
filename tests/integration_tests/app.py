from fastapi import Depends, FastAPI, Header, HTTPException, status
from typing import Optional

from fastapi_decorators import add_dependencies

app = FastAPI()

fake_users_db = {
    "alice": {"username": "alice", "roles": ["user"]},
    "bob": {"username": "bob", "roles": ["admin"]},
}

def get_current_user(x_auth_token: Optional[str] = Header(None)):
    if x_auth_token is None or x_auth_token not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return fake_users_db[x_auth_token]

def require_admin(user=Depends(get_current_user)):
    if "admin" not in user["roles"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admins only",
        )

def log_request(user=Depends(get_current_user)):
    # Use logging instead of print for better testability
    import logging
    logger = logging.getLogger("app")
    logger.info(f"User {user['username']} made a request")

@app.get("/public")
def read_public():
    return {"message": "This is a public endpoint"}

@app.get("/users/me")
@add_dependencies(Depends(get_current_user))
def read_current_user(user=Depends(get_current_user)):
    return {"user": user}

@app.get("/admin")
@add_dependencies(Depends(require_admin), Depends(log_request))
def read_admin_data():
    return {"message": "This is admin data"}

@app.get("/error")
@add_dependencies(Depends(log_request))
def error_endpoint():
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal Server Error",
    )
