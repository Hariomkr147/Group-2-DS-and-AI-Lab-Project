from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..security import check_login, current_user, limit_login, make_token

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limit_login)])
def login(body: Credentials):
    if not check_login(body.username.strip(), body.password):
        raise HTTPException(401, "Wrong username or password")
    return TokenOut(access_token=make_token(), username=body.username.strip())


@router.get("/me")
def me(user: str = Depends(current_user)):
    return {"username": user}
