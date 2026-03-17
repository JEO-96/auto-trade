import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Union
import bot_manager
import models, schemas, auth
from crypto_utils import encrypt_token
from dependencies import get_db, get_current_user, get_current_user_any
from kakao_service import exchange_code_for_tokens, get_user_info, verify_token, KakaoAuthError
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=schemas.Token)
@limiter.limit("10/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not user.hashed_password or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/kakao", response_model=Union[schemas.Token, schemas.KakaoEmailRequired])
@limiter.limit("10/minute")
async def kakao_login_endpoint(request: Request, login_data: schemas.KakaoLogin, db: Session = Depends(get_db)):
    # 1. Exchange authorization code for tokens & get user info
    try:
        tokens = await exchange_code_for_tokens(login_data.code, login_data.redirect_uri)
        user_info = await get_user_info(tokens.access_token)
    except KakaoAuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    kakao_id = user_info.kakao_id
    kakao_token = tokens.access_token
    kakao_refresh = tokens.refresh_token
    nickname = user_info.nickname
    email = user_info.email

    if not email:
        return schemas.KakaoEmailRequired(
            requires_email=True,
            kakao_id=kakao_id,
            kakao_token=kakao_token,
            nickname=nickname,
        )

    # 2. Check if user exists or create new
    user = db.query(models.User).filter(models.User.kakao_id == kakao_id).first()

    is_new_user = False
    if not user:
        user_by_email = db.query(models.User).filter(models.User.email == email).first()
        if user_by_email:
            user = user_by_email
            user.kakao_id = kakao_id
        else:
            user = models.User(email=email, kakao_id=kakao_id, is_active=False)
            db.add(user)
            is_new_user = True

    # 닉네임은 최초 가입 시 또는 아직 없을 때만 카카오 닉네임으로 설정
    # (사용자가 커뮤니티에서 변경한 닉네임이 로그인마다 덮어씌워지는 것 방지)
    if not user.nickname:
        logger.warning(
            "[Auth] Nickname empty for user %s (id=%s), setting to kakao nickname: '%s'",
            email, getattr(user, 'id', 'new'), nickname,
        )
        user.nickname = nickname
    else:
        logger.info(
            "[Auth] Nickname preserved for user %s (id=%s): db='%s', kakao='%s'",
            email, user.id, user.nickname, nickname,
        )
    # 카카오 토큰 Fernet 암호화 후 저장
    user.kakao_access_token = encrypt_token(kakao_token)
    if kakao_refresh:
        user.kakao_refresh_token = encrypt_token(kakao_refresh)

    db.commit()
    db.refresh(user)

    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/kakao/complete", response_model=schemas.Token)
@limiter.limit("10/minute")
async def kakao_complete_register(request: Request, data: schemas.KakaoCompleteRegister, db: Session = Depends(get_db)):
    """카카오 로그인 시 이메일 미제공 유저가 이메일 직접 입력 후 가입 완료하는 엔드포인트"""
    try:
        kakao_id_from_token = await verify_token(data.kakao_token)
    except KakaoAuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Kakao token. Please login again.")

    if kakao_id_from_token != data.kakao_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kakao ID mismatch.")

    # Check email uniqueness
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 이메일입니다.")

    # Create or link user
    is_new_user = False
    user = db.query(models.User).filter(models.User.kakao_id == data.kakao_id).first()
    if not user:
        user = models.User(email=data.email, kakao_id=data.kakao_id, nickname=data.nickname, is_active=False)
        db.add(user)
        is_new_user = True
    else:
        user.email = data.email

    # 카카오 토큰 Fernet 암호화 후 저장
    user.kakao_access_token = encrypt_token(data.kakao_token)
    # kakao_complete_register에서는 refresh_token이 없으므로 기존 값 유지
    db.commit()
    db.refresh(user)

    access_token = auth.create_access_token(
        data={"sub": user.email},
        expires_delta=auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user_any), db: Session = Depends(get_db)):
    return schemas.UserResponse(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        telegram_chat_id=current_user.telegram_chat_id,
        notification_trade=current_user.notification_trade if current_user.notification_trade is not None else True,
        notification_bot_status=current_user.notification_bot_status if current_user.notification_bot_status is not None else True,
        notification_system=current_user.notification_system if current_user.notification_system is not None else True,
        notification_interval=current_user.notification_interval or "realtime",
    )


@router.get("/notifications", response_model=schemas.NotificationSettings)
def get_notification_settings(current_user: models.User = Depends(get_current_user)):
    """현재 알림 설정 조회"""
    return schemas.NotificationSettings(
        notification_trade=current_user.notification_trade if current_user.notification_trade is not None else True,
        notification_bot_status=current_user.notification_bot_status if current_user.notification_bot_status is not None else True,
        notification_system=current_user.notification_system if current_user.notification_system is not None else True,
        notification_interval=current_user.notification_interval or "realtime",
    )


@router.put("/notifications", response_model=schemas.NotificationSettings)
def update_notification_settings(
    data: schemas.NotificationSettings,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """알림 설정 업데이트"""
    # notification_interval 유효성 검증
    valid_intervals = {"realtime", "4h", "12h", "daily"}
    if data.notification_interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"notification_interval은 {', '.join(sorted(valid_intervals))} 중 하나여야 합니다.",
        )
    current_user.notification_trade = data.notification_trade
    current_user.notification_bot_status = data.notification_bot_status
    current_user.notification_system = data.notification_system
    current_user.notification_interval = data.notification_interval
    db.commit()
    db.refresh(current_user)
    return schemas.NotificationSettings(
        notification_trade=current_user.notification_trade,
        notification_bot_status=current_user.notification_bot_status,
        notification_system=current_user.notification_system,
        notification_interval=current_user.notification_interval or "realtime",
    )


@router.delete("/withdraw")
async def withdraw_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """회원 탈퇴: 실행 중인 봇 정지 + 모든 사용자 데이터 삭제"""
    user_id = current_user.id

    # 1. 실행 중인 봇 정지
    user_bots = db.query(models.BotConfig).filter(models.BotConfig.user_id == user_id).all()
    for bot in user_bots:
        task = bot_manager.active_bots.get(bot.id)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass

    # 2. 관련 데이터 삭제 (순서 중요: FK 의존성)
    bot_ids = [b.id for b in user_bots]
    if bot_ids:
        db.query(models.ActivePosition).filter(models.ActivePosition.bot_id.in_(bot_ids)).delete(synchronize_session=False)
        db.query(models.TradeLog).filter(models.TradeLog.bot_id.in_(bot_ids)).delete(synchronize_session=False)
        db.query(models.BotConfig).filter(models.BotConfig.user_id == user_id).delete(synchronize_session=False)

    db.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == user_id).delete(synchronize_session=False)
    db.query(models.BacktestHistory).filter(models.BacktestHistory.user_id == user_id).delete(synchronize_session=False)
    db.query(models.PostLike).filter(models.PostLike.user_id == user_id).delete(synchronize_session=False)
    db.query(models.PostComment).filter(models.PostComment.user_id == user_id).delete(synchronize_session=False)
    db.query(models.CommunityPost).filter(models.CommunityPost.user_id == user_id).delete(synchronize_session=False)
    db.query(models.ChatMessage).filter(models.ChatMessage.user_id == user_id).delete(synchronize_session=False)

    # 크레딧 관련
    db.query(models.CreditTransaction).filter(models.CreditTransaction.user_id == user_id).delete(synchronize_session=False)
    db.query(models.PaymentOrder).filter(models.PaymentOrder.user_id == user_id).delete(synchronize_session=False)
    db.query(models.UserCredit).filter(models.UserCredit.user_id == user_id).delete(synchronize_session=False)

    # 3. 유저 삭제
    db.delete(current_user)
    db.commit()

    logger.info("User %d withdrew from the service.", user_id)
    return {"status": "success", "message": "회원 탈퇴가 완료되었습니다."}


# ──────────────────────────────────────────────
# 개발 전용 테스트 로그인 (프로덕션에서는 비활성화)
# ──────────────────────────────────────────────
_IS_DEV = os.environ.get("ENV", "dev") != "production"

if _IS_DEV:
    @router.post("/dev-login", response_model=schemas.Token)
    def dev_login(role: str = "user", db: Session = Depends(get_db)):
        """개발 전용: role='admin' 또는 'user'로 테스트 로그인.
        프로덕션 환경(ENV=production)에서는 이 엔드포인트가 등록되지 않음."""
        is_admin = role == "admin"
        email = "dev-admin@backtested.bot" if is_admin else "dev-user@backtested.bot"

        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            user = models.User(
                email=email,
                nickname="개발자" if is_admin else "테스트유저",
                is_active=True,
                is_admin=is_admin,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        access_token = auth.create_access_token(
            data={"sub": user.email},
            expires_delta=auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access_token, "token_type": "bearer"}
