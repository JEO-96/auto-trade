from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas
from dependencies import get_db, get_current_user
from crypto_utils import encrypt_key, decrypt_key

router = APIRouter(prefix="/keys", tags=["keys"])


@router.post("/", response_model=schemas.ExchangeKeyResponse)
def add_exchange_key(key_data: schemas.ExchangeKeyCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing_key = db.query(models.ExchangeKey).filter(
        models.ExchangeKey.user_id == current_user.id,
        models.ExchangeKey.exchange_name == key_data.exchange_name
    ).first()

    if existing_key:
        existing_key.api_key_encrypted = encrypt_key(key_data.api_key)
        existing_key.api_secret_encrypted = encrypt_key(key_data.api_secret)
        db_key = existing_key
    else:
        db_key = models.ExchangeKey(
            user_id=current_user.id,
            exchange_name=key_data.exchange_name,
            api_key_encrypted=encrypt_key(key_data.api_key),
            api_secret_encrypted=encrypt_key(key_data.api_secret)
        )
        db.add(db_key)

    db.commit()
    db.refresh(db_key)

    preview = key_data.api_key[:4] + "*" * 10
    return {"id": db_key.id, "exchange_name": db_key.exchange_name, "api_key_preview": preview}

@router.get("/", response_model=list[schemas.ExchangeKeyResponse])
def get_exchange_keys(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == current_user.id).all()
    results = []
    for k in keys:
        try:
            decrypted_key = decrypt_key(k.api_key_encrypted)
            preview = decrypted_key[:4] + "*" * 10 if len(decrypted_key) >= 4 else "****"
        except Exception:
            preview = "****"
        results.append({
            "id": k.id,
            "exchange_name": k.exchange_name,
            "api_key_preview": preview
        })
    return results
