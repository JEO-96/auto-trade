"""
AWS RDS 백업 상태 확인 및 데이터 무결성 체크 스크립트

기능:
  1. RDS 백업 상태 확인 (boto3) - 자동 백업, 스냅샷, 복구 가능 시간
  2. 데이터 무결성 체크 - 테이블 레코드 수, 외래키 참조 무결성
  3. PITR (Point-in-Time Recovery) 가이드 출력

사용법:
  cd backend
  python scripts/check_rds_backup.py

주의: 읽기 전용 스크립트 - 데이터를 수정하지 않음
"""

import sys
import os
from datetime import datetime, timezone

# backend/ 디렉토리를 path에 추가 (database.py, settings.py import 용)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from database import SessionLocal, engine
from settings import settings


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

def print_header(title: str) -> None:
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str) -> None:
    print(f"\n--- {title} ---")


def print_kv(key: str, value, indent: int = 2) -> None:
    prefix = " " * indent
    print(f"{prefix}{key}: {value}")


# ──────────────────────────────────────────────
# 1. RDS 백업 상태 확인 (boto3)
# ──────────────────────────────────────────────

def check_rds_backup() -> bool:
    """boto3로 RDS 인스턴스 백업 상태를 확인한다. boto3가 없으면 False를 반환."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError, NoRegionError
    except ImportError:
        print_section("RDS 백업 상태 확인 (boto3)")
        print("  [건너뜀] boto3가 설치되어 있지 않습니다.")
        print("  설치: pip install boto3")
        print("  AWS 자격 증명도 필요합니다 (~/.aws/credentials 또는 환경 변수)")
        return False

    print_header("1. AWS RDS 백업 상태 확인")

    # RDS 엔드포인트에서 리전 추출 시도
    db_host = settings.db_host
    region = _extract_region_from_host(db_host)

    try:
        rds_client = boto3.client("rds", region_name=region) if region else boto3.client("rds")
    except (NoCredentialsError, NoRegionError) as e:
        print(f"  [오류] AWS 자격 증명/리전 설정 필요: {e}")
        print("  환경 변수 설정: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION")
        return False

    # DB 인스턴스 목록에서 호스트와 매칭되는 인스턴스 찾기
    try:
        instances = rds_client.describe_db_instances()
        target_instance = None

        for inst in instances["DBInstances"]:
            endpoint = inst.get("Endpoint", {})
            if endpoint.get("Address", "") == db_host:
                target_instance = inst
                break

        if not target_instance:
            print(f"  [경고] DB 호스트({db_host})와 매칭되는 RDS 인스턴스를 찾지 못했습니다.")
            print("  Lightsail DB이거나, 다른 리전이거나, 자격 증명 권한이 부족할 수 있습니다.")
            _print_pitr_guide_generic(db_host)
            return False

        _print_instance_info(target_instance)
        _print_snapshots(rds_client, target_instance["DBInstanceIdentifier"])
        return True

    except ClientError as e:
        print(f"  [오류] RDS API 호출 실패: {e}")
        return False


def _extract_region_from_host(host: str) -> str | None:
    """RDS/Lightsail 엔드포인트에서 AWS 리전을 추출한다."""
    # 형식: xxx.yyy.{region}.rds.amazonaws.com
    parts = host.split(".")
    for i, part in enumerate(parts):
        if part == "rds" and i > 0:
            return parts[i - 1]
        # Lightsail: xxx.{region}.rds.amazonaws.com 도 동일 패턴
    return None


def _print_instance_info(instance: dict) -> None:
    """RDS 인스턴스 백업 관련 정보를 출력한다."""
    print_section("인스턴스 정보")
    print_kv("DB 식별자", instance.get("DBInstanceIdentifier"))
    print_kv("엔진", f"{instance.get('Engine')} {instance.get('EngineVersion')}")
    print_kv("인스턴스 클래스", instance.get("DBInstanceClass"))
    print_kv("상태", instance.get("DBInstanceStatus"))
    print_kv("멀티AZ", instance.get("MultiAZ"))
    print_kv("스토리지 암호화", instance.get("StorageEncrypted"))

    print_section("백업 설정")
    retention = instance.get("BackupRetentionPeriod", 0)
    print_kv("자동 백업", "활성화" if retention > 0 else "비활성화 [경고]")
    print_kv("백업 보존 기간", f"{retention}일")
    print_kv("백업 윈도우 (UTC)", instance.get("PreferredBackupWindow", "미설정"))
    print_kv("유지보수 윈도우", instance.get("PreferredMaintenanceWindow", "미설정"))

    latest_restorable = instance.get("LatestRestorableTime")
    if latest_restorable:
        now = datetime.now(timezone.utc)
        age = now - latest_restorable.replace(tzinfo=timezone.utc)
        print_kv("최근 복구 가능 시점", latest_restorable.strftime("%Y-%m-%d %H:%M:%S UTC"))
        print_kv("복구 가능 시점 경과", f"{age.total_seconds() / 60:.0f}분 전")
    else:
        print_kv("최근 복구 가능 시점", "정보 없음")

    # 백업 보존 기간 권장 사항
    if retention < 7:
        print(f"\n  [권장] 백업 보존 기간이 {retention}일입니다. 최소 7일 이상을 권장합니다.")
        print("  변경: AWS 콘솔 > RDS > 인스턴스 수정 > 백업 보존 기간")


def _print_snapshots(rds_client, db_identifier: str) -> None:
    """최근 자동 스냅샷 5개를 출력한다."""
    print_section("최근 자동 스냅샷 (최대 5개)")
    try:
        response = rds_client.describe_db_snapshots(
            DBInstanceIdentifier=db_identifier,
            SnapshotType="automated",
            MaxRecords=20,
        )
        snapshots = sorted(
            response.get("DBSnapshots", []),
            key=lambda s: s.get("SnapshotCreateTime", datetime.min),
            reverse=True,
        )[:5]

        if not snapshots:
            print("  스냅샷이 없습니다.")
            return

        for i, snap in enumerate(snapshots, 1):
            created = snap.get("SnapshotCreateTime", "")
            if hasattr(created, "strftime"):
                created = created.strftime("%Y-%m-%d %H:%M:%S UTC")
            size = snap.get("AllocatedStorage", "?")
            status = snap.get("Status", "?")
            print(f"  [{i}] {snap.get('DBSnapshotIdentifier', '?')}")
            print(f"      생성: {created} | 크기: {size}GB | 상태: {status}")

    except Exception as e:
        print(f"  스냅샷 조회 실패: {e}")


# ──────────────────────────────────────────────
# 2. 데이터 무결성 체크
# ──────────────────────────────────────────────

# 모든 테이블과 외래키 관계 정의 (models.py 기반)
TABLES = [
    "users",
    "exchange_keys",
    "bot_configs",
    "trade_logs",
    "ohlcv_data",
    "backtest_history",
    "active_positions",
    "community_posts",
    "post_comments",
    "post_likes",
    "system_settings",
    "user_credits",
    "credit_transactions",
    "payment_orders",
    "chat_messages",
]

# (child_table, child_fk_column, parent_table, parent_pk_column)
FOREIGN_KEYS = [
    ("exchange_keys", "user_id", "users", "id"),
    ("bot_configs", "user_id", "users", "id"),
    ("trade_logs", "bot_id", "bot_configs", "id"),
    ("backtest_history", "user_id", "users", "id"),
    ("active_positions", "bot_id", "bot_configs", "id"),
    ("community_posts", "user_id", "users", "id"),
    ("post_comments", "post_id", "community_posts", "id"),
    ("post_comments", "user_id", "users", "id"),
    ("post_likes", "post_id", "community_posts", "id"),
    ("post_likes", "user_id", "users", "id"),
    ("user_credits", "user_id", "users", "id"),
    ("credit_transactions", "user_id", "users", "id"),
    ("payment_orders", "user_id", "users", "id"),
    ("chat_messages", "user_id", "users", "id"),
]


def check_data_integrity() -> None:
    """각 테이블 레코드 수와 외래키 참조 무결성을 확인한다."""
    print_header("2. 데이터 무결성 체크")

    db = SessionLocal()
    try:
        # 2-1. 테이블별 레코드 수
        print_section("테이블별 레코드 수")
        total_records = 0
        table_counts: dict[str, int] = {}

        for table in TABLES:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                table_counts[table] = count
                total_records += count
                status = "" if count > 0 else " (비어 있음)"
                print(f"  {table:30s} {count:>8,d}{status}")
            except Exception as e:
                print(f"  {table:30s} [오류] {e}")
                table_counts[table] = -1

        print(f"\n  {'합계':30s} {total_records:>8,d}")

        # 2-2. 외래키 참조 무결성 (orphaned records)
        print_section("외래키 참조 무결성 체크")
        orphan_found = False

        for child_table, child_col, parent_table, parent_col in FOREIGN_KEYS:
            try:
                query = text(
                    f"SELECT COUNT(*) FROM {child_table} c "
                    f"LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col} "
                    f"WHERE p.{parent_col} IS NULL AND c.{child_col} IS NOT NULL"
                )
                result = db.execute(query)
                orphan_count = result.scalar()

                if orphan_count > 0:
                    orphan_found = True
                    print(f"  [경고] {child_table}.{child_col} -> {parent_table}.{parent_col}: "
                          f"고아 레코드 {orphan_count}건")
                else:
                    print(f"  [OK] {child_table}.{child_col} -> {parent_table}.{parent_col}")

            except Exception as e:
                print(f"  [오류] {child_table}.{child_col}: {e}")

        if not orphan_found:
            print("\n  모든 외래키 참조가 정상입니다.")
        else:
            print("\n  [주의] 고아 레코드가 발견되었습니다. 수동 점검이 필요합니다.")

        # 2-3. 핵심 비즈니스 데이터 요약
        print_section("핵심 비즈니스 데이터 요약")
        _print_business_summary(db)

    finally:
        db.close()


def _print_business_summary(db) -> None:
    """비즈니스 관점에서 중요한 데이터 요약을 출력한다."""
    summaries = [
        ("활성 사용자 수", "SELECT COUNT(*) FROM users WHERE is_active = true"),
        ("관리자 수", "SELECT COUNT(*) FROM users WHERE is_admin = true"),
        ("활성 봇 수", "SELECT COUNT(*) FROM bot_configs WHERE is_active = true"),
        ("실매매 봇 수", "SELECT COUNT(*) FROM bot_configs WHERE paper_trading_mode = false"),
        ("총 거래 건수", "SELECT COUNT(*) FROM trade_logs"),
        ("수익 거래 건수", "SELECT COUNT(*) FROM trade_logs WHERE pnl > 0"),
        ("커뮤니티 게시글 수", "SELECT COUNT(*) FROM community_posts WHERE is_deleted = false"),
        ("크레딧 보유 사용자", "SELECT COUNT(*) FROM user_credits WHERE balance > 0"),
    ]

    for label, query in summaries:
        try:
            result = db.execute(text(query))
            value = result.scalar()
            print_kv(label, f"{value:,d}")
        except Exception as e:
            print_kv(label, f"[오류] {e}")


# ──────────────────────────────────────────────
# 3. PITR 복구 가이드
# ──────────────────────────────────────────────

def print_pitr_guide() -> None:
    """Point-in-Time Recovery 가이드와 복구 후 체크리스트를 출력한다."""
    print_header("3. PITR (Point-in-Time Recovery) 가이드")

    db_host = settings.db_host
    _print_pitr_guide_generic(db_host)


def _print_pitr_guide_generic(db_host: str) -> None:
    """PITR 복구 명령어 예시와 체크리스트를 출력한다."""
    region = _extract_region_from_host(db_host) or "ap-northeast-2"

    print_section("boto3 복구 코드 예시")
    print(f"""
  import boto3
  from datetime import datetime, timezone

  rds = boto3.client("rds", region_name="{region}")

  # 복구 시점 지정 (UTC)
  restore_time = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)

  response = rds.restore_db_instance_to_point_in_time(
      SourceDBInstanceIdentifier="원본-인스턴스-이름",
      TargetDBInstanceIdentifier="restored-backtested-YYYYMMDD",
      RestoreTime=restore_time,
      DBInstanceClass="db.t3.micro",       # 원본과 동일하게
      PubliclyAccessible=False,
      MultiAZ=False,
      Tags=[
          {{"Key": "Purpose", "Value": "PITR-Recovery-Test"}},
          {{"Key": "RestoreDate", "Value": restore_time.isoformat()}},
      ],
  )
  print("복구 인스턴스 생성 시작:", response["DBInstance"]["DBInstanceIdentifier"])
""")

    print_section("AWS CLI 복구 명령어 예시")
    print(f"""
  # 1. 현재 복구 가능 시점 확인
  aws rds describe-db-instances \\
      --region {region} \\
      --query "DBInstances[].{{ID:DBInstanceIdentifier,LatestRestore:LatestRestorableTime}}" \\
      --output table

  # 2. Point-in-Time 복구 실행
  aws rds restore-db-instance-to-point-in-time \\
      --region {region} \\
      --source-db-instance-identifier "원본-인스턴스-이름" \\
      --target-db-instance-identifier "restored-backtested-$(date +%Y%m%d)" \\
      --restore-time "2026-03-15T12:00:00Z" \\
      --db-instance-class db.t3.micro \\
      --no-publicly-accessible

  # 3. 복구 완료 대기 (약 5~15분)
  aws rds wait db-instance-available \\
      --region {region} \\
      --db-instance-identifier "restored-backtested-$(date +%Y%m%d)"

  # 4. 복구된 인스턴스 엔드포인트 확인
  aws rds describe-db-instances \\
      --region {region} \\
      --db-instance-identifier "restored-backtested-$(date +%Y%m%d)" \\
      --query "DBInstances[0].Endpoint" \\
      --output json

  # 5. 테스트 완료 후 복구 인스턴스 삭제 (비용 절감)
  aws rds delete-db-instance \\
      --region {region} \\
      --db-instance-identifier "restored-backtested-$(date +%Y%m%d)" \\
      --skip-final-snapshot
""")

    print_section("복구 후 확인 체크리스트")
    checklist = [
        "복구된 DB에 접속 가능한지 확인 (psql 또는 pgAdmin)",
        "users 테이블 레코드 수가 원본과 일치하는지 확인",
        "bot_configs 테이블의 활성 봇 설정이 보존되었는지 확인",
        "trade_logs의 최근 거래 기록이 복구 시점까지 존재하는지 확인",
        "user_credits 잔액이 원본과 일치하는지 확인",
        "credit_transactions 이력이 누락 없이 복구되었는지 확인",
        "active_positions에 열린 포지션이 보존되었는지 확인",
        "community_posts, post_comments 데이터가 정상인지 확인",
        "외래키 참조 무결성 체크 (이 스크립트의 섹션 2 재실행)",
        "복구 테스트 완료 후 복구 인스턴스 반드시 삭제 (비용 발생 주의)",
    ]
    for i, item in enumerate(checklist, 1):
        print(f"  [{i:2d}] {item}")

    print_section("권장 백업 정책")
    recommendations = [
        "자동 백업 보존 기간: 최소 7일 (권장 14일)",
        "수동 스냅샷: 주요 배포 전/후 수동 스냅샷 생성",
        "정기 복구 테스트: 월 1회 PITR 복구 → 무결성 체크 → 삭제",
        "모니터링: CloudWatch 알람으로 백업 실패 감지",
        "다중 리전 복제: 재해복구(DR) 필요 시 cross-region 복제 고려",
    ]
    for item in recommendations:
        print(f"  - {item}")


# ──────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────

def main() -> None:
    print_header("Backtested DB 백업 검증 스크립트")
    print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DB 호스트: {settings.db_host}")
    print(f"  DB 이름:   {settings.db_name}")
    print("  모드: 읽기 전용 (데이터 수정 없음)")

    # 1. RDS 백업 상태 (boto3 optional)
    check_rds_backup()

    # 2. 데이터 무결성
    check_data_integrity()

    # 3. PITR 가이드
    print_pitr_guide()

    print_header("검증 완료")
    print("  이 스크립트를 정기적으로 실행하여 백업 상태를 점검하세요.")
    print("  권장 주기: 월 1회 (cron 또는 수동)")
    print()


if __name__ == "__main__":
    main()
