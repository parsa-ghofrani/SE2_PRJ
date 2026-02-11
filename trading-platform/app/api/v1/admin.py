from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User
from app.services.blockchain import BlockchainAdapter  # ✅ فقط کلاس را import کنید

router = APIRouter()


class SetAccessLevelRequest(BaseModel):
    user_address: str
    level: int


class IncidentRequest(BaseModel):
    description: str


@router.get("/admin/blockchain/owner")
def get_blockchain_owner(current_user: User = Depends(get_current_user)):
    """دریافت owner قرارداد بلاک چین"""
    try:
        adapter = BlockchainAdapter()  # ✅ اینجا instance بسازید
        owner = adapter.get_owner()
        return {"owner": owner}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/blockchain/access-level/{address}")
def get_access_level(address: str, current_user: User = Depends(get_current_user)):
    """بررسی سطح دسترسی یک آدرس"""
    try:
        adapter = BlockchainAdapter()  # ✅ اینجا instance بسازید
        level = adapter.get_access_level(address)
        level_names = {0: "NONE", 1: "READER", 2: "RECORDER", 3: "ADMIN"}
        return {
            "address": address,
            "level": level,
            "level_name": level_names.get(level, "UNKNOWN")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/blockchain/set-access")
def set_access_level(
    payload: SetAccessLevelRequest,
    current_user: User = Depends(get_current_user)
):
    """تنظیم سطح دسترسی (فقط برای ادمین)"""
    if payload.level not in [0, 1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid access level")
    
    try:
        adapter = BlockchainAdapter()  # ✅ اینجا instance بسازید
        tx_hash = adapter.set_access_level(
            payload.user_address,
            payload.level
        )
        return {
            "success": True,
            "tx_hash": tx_hash,
            "message": f"Access level set to {payload.level}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/incident/log")
def log_incident(
    payload: IncidentRequest,
    current_user: User = Depends(get_current_user)
):
    """ثبت حادثه روی بلاک چین"""
    try:
        adapter = BlockchainAdapter()  # ✅ اینجا instance بسازید
        tx_hash = adapter.log_incident(payload.description)
        return {
            "success": True,
            "tx_hash": tx_hash,
            "message": "Incident logged successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))