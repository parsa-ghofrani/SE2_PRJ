# app/schemas/siwe.py
from pydantic import BaseModel

class SiweLoginRequest(BaseModel):
    message: str
    signature: str

class SiweNonceResponse(BaseModel):
    nonce: str
