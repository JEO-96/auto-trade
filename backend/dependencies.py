from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import database, models, auth

get_db = database.get_db
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except auth.JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user

def get_current_user_optional(
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)),
    db: Session = Depends(get_db),
) -> models.User | None:
    """토큰이 없거나 유효하지 않으면 None을 반환하는 선택적 인증."""
    if not token:
        return None
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except auth.JWTError:
        return None
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not user.is_active:
        return None
    return user


def get_admin_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """관리자 권한 검증 의존성. is_admin이 True인 사용자만 허용."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


def get_user_or_404(db: Session, user_id: int) -> models.User:
    """ID로 사용자 조회. 없으면 404."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user
