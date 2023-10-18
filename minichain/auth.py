"""
JWT Authentication for api.py
-----------------------------
checks the JWT token in the Authorization header
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
import json
from uuid import uuid4


ALGORITHM = "HS256"


def get_or_create_secret_and_token():
    """Check if the JWT_SECRET environment variable exists in .vscode/settings.json[minichain.jwt_secret]"""
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        try:
            settings = None
            with open(".vscode/settings.json") as f:
                settings = json.load(f)
            secret = settings["minichain.jwt_secret"]
        except Exception as e:
            secret = uuid4().hex
            os.makedirs(".vscode", exist_ok=True)
            settings = settings or {}
            settings["minichain.jwt_secret"] = secret
            with open(".vscode/settings.json", "w") as f:
                json.dump(settings, f, indent=4)
    # check if a frontend token exists in .vscode/settings.json[minichain.token]
    try:
        token = settings["minichain.token"]
    except:
        token = create_access_token({"sub": "frontend", "scopes": ["root", "edit"]}, secret)
        settings["minichain.token"] = token
        with open(".vscode/settings.json", "w") as f:
            json.dump(settings, f, indent=4)
    print("Token for frontend:", token)
    return secret


def create_access_token(data: dict, secret: str = None):
    """Create a JWT token"""
    secret = secret or JWT_SECRET
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)
    return encoded_jwt

JWT_SECRET = get_or_create_secret_and_token()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_token_payload(token: str = Depends(oauth2_scheme)):
    """Check if the token is valid and return the payload"""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        print(token, JWT_SECRET)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_payload_or_none(token: str = Depends(oauth2_scheme)):
    """Check if the token is valid and return the payload"""
    try:
        print(token, JWT_SECRET)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None



if __name__ == "__main__":
    data = {"sub": "frontend", "scopes": ["root"]}
    test_token = create_access_token(data)
    print(get_token_payload(test_token))



"""
Usage example:

from minichain.auth import get_token_payload

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_token_payload)):
    return current_user
"""
    
