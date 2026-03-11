import logging

import ccxt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models, schemas
from dependencies import get_db, get_current_user
from crypto_utils import encrypt_key, decrypt_key

logger = logging.getLogger(__name__)

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


@router.delete("/{key_id}")
def delete_exchange_key(
    key_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key = db.query(models.ExchangeKey).filter(
        models.ExchangeKey.id == key_id,
        models.ExchangeKey.user_id == current_user.id,
    ).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API 키를 찾을 수 없습니다.",
        )
    db.delete(key)
    db.commit()
    return {"detail": "API 키가 삭제되었습니다."}


@router.get("/balance", response_model=schemas.BalanceResponse)
async def get_upbit_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch the current user's Upbit account balances via ccxt."""

    # 1. Look up the user's stored exchange key
    exchange_key = (
        db.query(models.ExchangeKey)
        .filter(
            models.ExchangeKey.user_id == current_user.id,
            models.ExchangeKey.exchange_name == "upbit",
        )
        .first()
    )
    if not exchange_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 Upbit API 키가 없습니다. 먼저 API 키를 등록해주세요.",
        )

    # 2. Decrypt credentials
    try:
        api_key = decrypt_key(exchange_key.api_key_encrypted)
        api_secret = decrypt_key(exchange_key.api_secret_encrypted)
    except Exception:
        logger.exception("Failed to decrypt exchange key for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키 복호화에 실패했습니다. 키를 다시 등록해주세요.",
        )

    # 3. Create ccxt upbit instance and fetch balance
    try:
        exchange = ccxt.upbit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        raw_balance = exchange.fetch_balance()
    except ccxt.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Upbit API 인증에 실패했습니다. API 키와 시크릿을 확인해주세요.",
        )
    except ccxt.NetworkError as exc:
        logger.warning("Network error fetching Upbit balance for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upbit 서버와의 통신에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )
    except ccxt.ExchangeError as exc:
        logger.warning("Exchange error fetching Upbit balance for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upbit 거래소 오류: {exc}",
        )

    # 4. Filter to non-zero balances and build response
    balances = []
    for currency, details in raw_balance.items():
        # Skip meta keys that ccxt adds (info, free, used, total, timestamp, datetime)
        if not isinstance(details, dict) or "total" not in details:
            continue
        total = details.get("total") or 0
        if total <= 0:
            continue

        # Upbit provides avg_buy_price in the raw info per currency
        avg_buy_price = None
        info_list = raw_balance.get("info", [])
        if isinstance(info_list, list):
            for entry in info_list:
                if isinstance(entry, dict) and entry.get("currency", "").upper() == currency.upper():
                    try:
                        avg_buy_price = float(entry["avg_buy_price"])
                    except (KeyError, ValueError, TypeError):
                        pass
                    break

        balances.append(
            schemas.BalanceItem(
                currency=currency,
                total=float(total),
                free=float(details.get("free") or 0),
                used=float(details.get("used") or 0),
                avg_buy_price=avg_buy_price,
            )
        )

    return schemas.BalanceResponse(balances=balances)
