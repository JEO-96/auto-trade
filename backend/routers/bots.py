from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import asyncio
import models, schemas, bot_manager
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/bot", tags=["bots"])

@router.post("/start/{bot_id}")
async def start_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot_config = db.query(models.BotConfig).filter(models.BotConfig.id == bot_id, models.BotConfig.user_id == current_user.id).first()
    if not bot_config:
        return {"status": "error", "message": "Bot configuration not found."}
        
    if bot_id in bot_manager.active_bots and not bot_manager.active_bots[bot_id].done():
        return {"status": "error", "message": "Bot already running."}
        
    task = asyncio.create_task(bot_manager.run_bot_loop(bot_id))
    bot_manager.active_bots[bot_id] = task
    
    return {"status": "success", "message": f"Bot {bot_id} started."}

@router.post("/stop/{bot_id}")
async def stop_bot(bot_id: int, current_user: models.User = Depends(get_current_user)):
    if bot_id in bot_manager.active_bots:
        task = bot_manager.active_bots.pop(bot_id)
        task.cancel() 
        return {"status": "success", "message": f"Bot {bot_id} stopped."}
    return {"status": "error", "message": "Bot was not running."}

@router.get("/status/{bot_id}")
def status_bot(bot_id: int, current_user: models.User = Depends(get_current_user)):
    status = bot_manager.get_bot_status(bot_id)
    return {"status": "success", "bot_status": status}

@router.get("/logs/{bot_id}", response_model=list[schemas.TradeLogResponse])
def get_bot_trade_logs(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(models.TradeLog).filter(models.TradeLog.bot_id == bot_id).order_by(models.TradeLog.id.desc()).all()
    return logs
