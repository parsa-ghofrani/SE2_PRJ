from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import RegisterIn, TokenOut, UserOut

from app.schemas.siwe import SiweLoginRequest, SiweNonceResponse
from app.services.siwe import generate_nonce, parse_siwe_message, recover_address
from app.services.siwe_nonce_store import put_nonce, consume_nonce

router = APIRouter()


@router.post("/auth/register", response_model=UserOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        wallet_address=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.password_hash == "DISABLED":
        raise HTTPException(status_code=401, detail="User password is disabled; re-register")

    if not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(subject=str(user.id))
    return TokenOut(access_token=token)


@router.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# -----------------------------
# SIWE (EIP-4361) AUTH (BONUS)
# -----------------------------

@router.get("/auth/siwe/nonce", response_model=SiweNonceResponse)
def siwe_nonce():
    nonce = generate_nonce()
    put_nonce(nonce)
    return SiweNonceResponse(nonce=nonce)


@router.post("/auth/siwe/login", response_model=TokenOut)
def siwe_login(payload: SiweLoginRequest, db: Session = Depends(get_db)):
    # 1) Parse SIWE message
    try:
        msg = parse_siwe_message(payload.message)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid SIWE message")

    # 2) Nonce must exist and be unused (anti-replay)
    if not consume_nonce(msg.nonce):
        raise HTTPException(status_code=401, detail="Invalid or expired nonce")

    # 3) Basic domain/origin checks (recommended)
    app_domain = os.environ.get("APP_DOMAIN", "localhost")
    app_origin = os.environ.get("APP_ORIGIN", "http://localhost:8000")

    if msg.domain != app_domain:
        raise HTTPException(status_code=401, detail="Invalid SIWE domain")

    if not msg.uri.startswith(app_origin):
        raise HTTPException(status_code=401, detail="Invalid SIWE URI")

    # 4) Verify signature matches address in message
    try:
        recovered = recover_address(payload.message, payload.signature)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid signature")

    if recovered != msg.address:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 5) Find-or-create user by wallet_address
    user = db.query(User).filter(User.wallet_address == msg.address).first()
    if not user:
        # ensure username is unique; simplest deterministic username for wallet users
        base = f"wallet_{msg.address[:8].lower()}"
        username = base
        i = 1
        while db.query(User).filter(User.username == username).first():
            i += 1
            username = f"{base}_{i}"

        user = User(
            username=username,
            password_hash="DISABLED",  # wallet-only account (no password login)
            wallet_address=msg.address,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 6) Issue JWT (same as normal login)
    token = create_access_token(subject=str(user.id))
    return TokenOut(access_token=token)
