from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth
from dependencies import get_db, get_current_user
import httpx
from core import config

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval pending. Please contact admin.")
    
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/kakao", response_model=schemas.Token)
async def kakao_login_endpoint(login_data: schemas.KakaoLogin, db: Session = Depends(get_db)):
    # 1. Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        token_url = "https://kauth.kakao.com/oauth/token"
        token_params = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": login_data.redirect_uri,
            "code": login_data.code,
        }
        
        token_response = await client.post(token_url, data=token_params)
        
        if token_response.status_code != 200:
            print(f"Kakao token error: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Failed to get Kakao access token: {token_response.text}"
            )
        
        kakao_token = token_response.json().get("access_token")
        
        # 2. Get user information using the access token
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_info_response = await client.get(
            user_info_url, 
            headers={"Authorization": f"Bearer {kakao_token}"}
        )
        
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Failed to get Kakao user info"
            )
        
        user_json = user_info_response.json()
        kakao_id = str(user_json.get("id"))
        kakao_account = user_json.get("kakao_account", {})
        properties = user_json.get("properties", {})
        nickname = properties.get("nickname")
        email = kakao_account.get("email")
        
        if not email:
            # Fallback for users without email permission
            email = f"{kakao_id}@kakao.com"
            
        # 3. Check if user exists or create new
        user = db.query(models.User).filter(models.User.kakao_id == kakao_id).first()
        
        if not user:
            # Check if a user with the same email already exists
            user_by_email = db.query(models.User).filter(models.User.email == email).first()
            if user_by_email:
                user = user_by_email
                user.kakao_id = kakao_id
            else:
                user = models.User(email=email, kakao_id=kakao_id)
                db.add(user)
        
        # Always update nickname and access token from Kakao
        user.nickname = nickname
        user.kakao_access_token = kakao_token
        
        db.commit()
        db.refresh(user)
            
        # 4. Check if user is approved (active)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="승인 대기 중입니다. 관리자에게 문의하세요."
            )
            
        # 5. Generate application JWT token
        access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.email}, 
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user
