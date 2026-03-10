import httpx
import json
from models import User
from sqlalchemy.orm import Session
import database

async def send_kakao_message(user_id: int, message: str):
    """
    Sends a KakaoTalk message to the user using 'Send to Me' (FREE).
    Creates its own DB session to avoid sharing request-scoped sessions
    across async task boundaries.
    """
    db = None
    try:
        db = database.SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.kakao_access_token:
            print(f"User {user_id} not found or no Kakao access token.")
            return False

        kakao_token = user.kakao_access_token
    except Exception as e:
        print(f"Error querying user for Kakao message: {e}")
        return False
    finally:
        if db:
            db.close()

    try:
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {
            "Authorization": f"Bearer {kakao_token}"
        }

        # Simple feed template for "Send to Me"
        template_object = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://jooeunoh.com",
                "mobile_web_url": "https://jooeunoh.com"
            },
            "button_title": "대시보드 보기"
        }

        payload = {
            "template_object": json.dumps(template_object)
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                print(f"Successfully sent Kakao message to user {user_id}")
                return True
            else:
                print(f"Failed to send Kakao message: {response.text}")
                return False

    except Exception as e:
        print(f"Error sending Kakao message: {e}")
        return False
