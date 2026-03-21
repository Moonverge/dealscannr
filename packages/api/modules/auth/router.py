from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from bson import ObjectId
from fastapi import APIRouter

from modules.api_errors import raise_api_error
from pydantic import BaseModel, Field

from config.settings import settings
from db.mongo import get_database
from modules.auth.deps import CurrentUser

router = APIRouter()


class RegisterBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class LoginBody(BaseModel):
    email: str
    password: str


def _issue_token(user_id: ObjectId) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(
        {"sub": str(user_id), "exp": exp},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/auth/register")
async def auth_register(body: RegisterBody):
    db = get_database()
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise_api_error(
            status_code=409,
            error="conflict",
            message="Email already registered",
        )
    hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt())
    doc = {
        "email": email,
        "password_hash": hashed.decode("utf-8"),
        "plan_tier": "free",
        "scan_credits": 3,
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.users.insert_one(doc)
    token = _issue_token(res.inserted_id)
    return {"user_id": str(res.inserted_id), "token": token}


@router.post("/auth/login")
async def auth_login(body: LoginBody):
    db = get_database()
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid email or password",
        )
    ok = bcrypt.checkpw(
        body.password.encode("utf-8"),
        str(user["password_hash"]).encode("utf-8"),
    )
    if not ok:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid email or password",
        )
    token = _issue_token(user["_id"])
    return {"token": token}


@router.get("/auth/me")
async def auth_me(user: CurrentUser):
    """Requires Bearer token; returns user id, credits, plan."""
    return {
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "plan_tier": user.get("plan_tier", "free"),
            "scan_credits": user.get("scan_credits", 0),
        },
        "credits": user.get("scan_credits", 0),
        "plan": user.get("plan_tier", "free"),
    }
