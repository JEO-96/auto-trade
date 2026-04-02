import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import models, schemas
from dependencies import get_db, get_current_user, get_admin_user
from crypto_utils import encrypt_key, decrypt_key, mask_api_key, fetch_exchange_balance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keys", tags=["keys"])


@router.post("/", response_model=schemas.ExchangeKeyResponse)
def add_exchange_key(key_data: schemas.ExchangeKeyCreate, current_user: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    existing_key = db.query(models.ExchangeKey).filter(
        models.ExchangeKey.user_id == current_user.id,
        models.ExchangeKey.exchange_name == key_data.exchange_name
    ).first()

    passphrase_enc = encrypt_key(key_data.passphrase) if key_data.passphrase else None

    if existing_key:
        existing_key.api_key_encrypted = encrypt_key(key_data.api_key)
        existing_key.api_secret_encrypted = encrypt_key(key_data.api_secret)
        existing_key.passphrase_encrypted = passphrase_enc
        db_key = existing_key
    else:
        db_key = models.ExchangeKey(
            user_id=current_user.id,
            exchange_name=key_data.exchange_name,
            api_key_encrypted=encrypt_key(key_data.api_key),
            api_secret_encrypted=encrypt_key(key_data.api_secret),
            passphrase_encrypted=passphrase_enc,
        )
        db.add(db_key)

    db.commit()
    db.refresh(db_key)

    return {"id": db_key.id, "exchange_name": db_key.exchange_name, "api_key_preview": mask_api_key(key_data.api_key)}

@router.get("/", response_model=list[schemas.ExchangeKeyResponse])
def get_exchange_keys(current_user: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    keys = db.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == current_user.id).all()
    results = []
    for k in keys:
        try:
            preview = mask_api_key(decrypt_key(k.api_key_encrypted))
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
    current_user: models.User = Depends(get_admin_user),
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
async def get_exchange_balance(
    exchange_name: str = Query("upbit", description="거래소 이름 (upbit, bithumb)"),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Fetch the current user's exchange account balances via ccxt."""

    # 공통 함수로 잔고 조회 (ExchangeKey 조회, 복호화, ccxt 호출, 에러 처리 포함)
    raw_balance = fetch_exchange_balance(current_user.id, exchange_name, db)

    # Filter to non-zero balances and build response
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


# 캐시: 마켓 목록은 자주 바뀌지 않으므로 메모리 캐시 (1시간)
_markets_cache: dict[str, dict] = {}
_markets_cache_time: dict[str, float] = {}
MARKETS_CACHE_TTL = 3600  # 1시간


@router.get("/markets")
async def get_exchange_markets(
    exchange_name: str = Query("upbit", description="거래소 이름 (upbit, bithumb)"),
):
    """거래소에서 KRW 마켓의 거래 가능한 심볼 목록을 조회합니다."""
    import ccxt
    import time

    now = time.time()
    cache_key = exchange_name

    # 캐시 히트
    if cache_key in _markets_cache and (now - _markets_cache_time.get(cache_key, 0)) < MARKETS_CACHE_TTL:
        return _markets_cache[cache_key]

    try:
        if exchange_name == "upbit":
            exchange = ccxt.upbit()
        elif exchange_name == "bithumb":
            exchange = ccxt.bithumb()
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 거래소: {exchange_name}")

        markets = exchange.load_markets()

        # KRW 마켓만 필터 + 활성 마켓만
        symbols = sorted([
            symbol for symbol, market in markets.items()
            if market.get('quote') == 'KRW' and market.get('active', True)
        ])

        result = {"exchange": exchange_name, "symbols": symbols, "count": len(symbols)}
        _markets_cache[cache_key] = result
        _markets_cache_time[cache_key] = now

        return result
    except ccxt.NetworkError as e:
        raise HTTPException(status_code=502, detail=f"거래소 연결 실패: {str(e)}")
    except Exception as e:
        logger.error("[Markets] Failed to load markets for %s: %s", exchange_name, e)
        raise HTTPException(status_code=500, detail="마켓 목록 조회에 실패했습니다.")
