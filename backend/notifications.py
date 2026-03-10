import httpx
import json
from models import User
from sqlalchemy.orm import Session
import database
from core import config


async def _refresh_kakao_token(user_id: int, refresh_token: str) -> str | None:
    """
    카카오 refresh_token으로 새 access_token을 발급받고 DB에 저장.
    성공 시 새 access_token 반환, 실패 시 None 반환.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": config.KAKAO_REST_API_KEY,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                print(f"[Kakao] Token refresh failed for user {user_id}: {response.text}")
                return None

            token_data = response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")  # 갱신 시 새 refresh_token이 올 수도 있음

            if not new_access_token:
                return None

            # DB에 새 토큰 저장
            db = database.SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.kakao_access_token = new_access_token
                    if new_refresh_token:
                        user.kakao_refresh_token = new_refresh_token
                    db.commit()
                    print(f"[Kakao] Token refreshed for user {user_id}")
            except Exception as e:
                db.rollback()
                print(f"[Kakao] Failed to save refreshed token: {e}")
            finally:
                db.close()

            return new_access_token

    except Exception as e:
        print(f"[Kakao] Token refresh error for user {user_id}: {e}")
        return None


async def _send_message(kakao_token: str, message: str) -> int:
    """카카오톡 나에게 보내기 실행. HTTP 상태코드 반환."""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {kakao_token}"}
    template_object = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://jooeunoh.com",
            "mobile_web_url": "https://jooeunoh.com",
        },
        "button_title": "대시보드 보기",
    }
    payload = {"template_object": json.dumps(template_object)}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, data=payload)
        return response.status_code


async def send_kakao_message(user_id: int, message: str) -> bool:
    """
    카카오톡 나에게 보내기 (무료).
    토큰 만료(401) 시 refresh_token으로 자동 갱신 후 재시도.
    """
    db = None
    try:
        db = database.SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.kakao_access_token:
            print(f"[Kakao] User {user_id}: no access token")
            return False

        kakao_token = user.kakao_access_token
        refresh_token = user.kakao_refresh_token
    except Exception as e:
        print(f"[Kakao] DB error for user {user_id}: {e}")
        return False
    finally:
        if db:
            db.close()

    try:
        # 1차 시도
        status_code = await _send_message(kakao_token, message)

        if status_code == 200:
            print(f"[Kakao] Message sent to user {user_id}")
            return True

        # 401 = 토큰 만료 → refresh 시도
        if status_code == 401 and refresh_token:
            print(f"[Kakao] Token expired for user {user_id}, refreshing...")
            new_token = await _refresh_kakao_token(user_id, refresh_token)

            if new_token:
                # 2차 시도 (갱신된 토큰으로)
                retry_status = await _send_message(new_token, message)
                if retry_status == 200:
                    print(f"[Kakao] Message sent after token refresh for user {user_id}")
                    return True
                else:
                    print(f"[Kakao] Retry failed for user {user_id}: status {retry_status}")
            else:
                print(f"[Kakao] Token refresh failed for user {user_id}")
        else:
            print(f"[Kakao] Send failed for user {user_id}: status {status_code}")

        return False

    except Exception as e:
        print(f"[Kakao] Error sending message to user {user_id}: {e}")
        return False
