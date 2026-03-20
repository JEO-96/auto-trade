"""
Migration: 기존 users 테이블의 kakao_access_token, kakao_refresh_token 평문을 Fernet 암호화.

안전하게 여러 번 실행 가능:
- 이미 암호화된 토큰 (gAAAAA 접두사)은 건너뜀
- None/빈 문자열은 건너뜀
"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
import database
from crypto_utils import encrypt_key, FERNET_PREFIX


def migrate():
    with database.engine.connect() as conn:
        # 카카오 토큰이 있는 유저 조회
        rows = conn.execute(text(
            "SELECT id, kakao_access_token, kakao_refresh_token FROM users "
            "WHERE kakao_access_token IS NOT NULL OR kakao_refresh_token IS NOT NULL"
        )).fetchall()

        if not rows:
            print("[INFO] 카카오 토큰이 있는 유저가 없습니다.")
            print("[DONE] 마이그레이션 완료 (변경 없음)")
            return

        updated_count = 0
        skipped_count = 0

        for row in rows:
            user_id = row[0]
            access_token = row[1]
            refresh_token = row[2]

            new_access = None
            new_refresh = None
            needs_update = False

            # access_token 암호화
            if access_token and not access_token.startswith(FERNET_PREFIX):
                new_access = encrypt_key(access_token)
                needs_update = True

            # refresh_token 암호화
            if refresh_token and not refresh_token.startswith(FERNET_PREFIX):
                new_refresh = encrypt_key(refresh_token)
                needs_update = True

            if not needs_update:
                skipped_count += 1
                continue

            # 변경된 필드만 업데이트
            updates = []
            params = {"uid": user_id}

            if new_access:
                updates.append("kakao_access_token = :at")
                params["at"] = new_access
            if new_refresh:
                updates.append("kakao_refresh_token = :rt")
                params["rt"] = new_refresh

            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = :uid"
            conn.execute(text(sql), params)
            updated_count += 1

        conn.commit()

        print(f"[OK] 암호화 완료: {updated_count}명 업데이트, {skipped_count}명 건너뜀 (이미 암호화됨)")
        print("[DONE] 마이그레이션 완료")


if __name__ == "__main__":
    migrate()
