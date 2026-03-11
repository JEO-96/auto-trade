"""
트레이드 로깅 모듈 — 매매 기록을 DB에 저장.

bot_manager.py에서 분리된 거래 로그 저장 함수.
"""
import logging
from datetime import datetime
from typing import Optional

import database
import models

logger = logging.getLogger(__name__)


def save_trade_log(
    bot_id: int,
    symbol: str,
    side: str,
    price: float,
    amount: float,
    reason: str,
    pnl: Optional[float] = None,
) -> None:
    """매매 기록을 trade_logs 테이블에 저장"""
    with database.get_db_session() as db:
        try:
            log = models.TradeLog(
                bot_id=bot_id,
                symbol=symbol,
                side=side,
                price=price,
                amount=amount,
                pnl=pnl,
                reason=reason,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to save trade log: %s", e)
