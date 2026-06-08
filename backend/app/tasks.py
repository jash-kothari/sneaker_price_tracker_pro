import asyncio
import json
import random
import datetime
import httpx
import redis
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from app.worker import celery_app
from app.database import async_session
from app import crud, models
from app.config import settings
from app.scrapers import run_scraper

# Helper to run async code inside Celery's sync worker threads
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Redis client for broadcasting updates
redis_client = redis.Redis.from_url(settings.REDIS_URL)

def publish_ws_event(event_type: str, data: dict):
    """Publish update to Redis Pub/Sub for FastAPI WebSockets to consume"""
    try:
        payload = {"type": event_type, "data": data}
        redis_client.publish("solesentry_updates", json.dumps(payload))
    except Exception as e:
        print(f"[Redis PubSub] Failed to publish event: {str(e)}")

async def send_telegram_alert(message: str):
    """Send alert via Telegram API directly to all active subscribers"""
    if settings.TELEGRAM_BOT_TOKEN == "TELEGRAM_BOT_TOKEN_PLACEHOLDER":
        print("[Telegram Bot] Bot token not set. Skipping alerts.")
        return
        
    async with async_session() as db:
        users = await crud.get_telegram_users(db)
        if not users:
            return
            
        async with httpx.AsyncClient() as client:
            for user in users:
                try:
                    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                    payload = {"chat_id": user.chat_id, "text": message, "parse_mode": "HTML"}
                    await client.post(url, json=payload, timeout=8.0)
                except Exception as e:
                    print(f"[Telegram Bot] Failed to alert chat {user.chat_id}: {str(e)}")

def simulate_price_update(original_price: float, current_price: float):
    roll = random.random()
    new_price = current_price
    
    if roll > 0.6 and roll <= 0.85:
        # Price drop: 2% to 12% discount
        discount = random.uniform(0.02, 0.12)
        new_price = round(current_price * (1 - discount), 2)
    elif roll > 0.85:
        # Price increase: 1% to 5%
        hike = random.uniform(0.01, 0.05)
        new_price = round(current_price * (1 + hike), 2)
        
    # Min 40% / Max 130% of original retail price
    min_p = round(original_price * 0.4, 2)
    max_p = round(original_price * 1.3, 2)
    if new_price < min_p: new_price = min_p
    if new_price > max_p: new_price = max_p
    
    status = "Stable"
    if new_price < current_price:
        status = "Dropped"
    elif new_price > current_price:
        status = "Increased"
        
    return new_price, status


async def check_sneaker_price_async(sneaker_id: int):
    async with async_session() as db:
        sneaker = await crud.get_sneaker(db, sneaker_id)
        if not sneaker or not sneaker.is_active:
            return
            
        old_price = sneaker.current_price
        new_price = old_price
        status = "Stable"
        updates_type = sneaker.updates_type
        image = sneaker.image
        name = sneaker.name
        
        if updates_type == "Simulated Crawler":
            new_price, status = simulate_price_update(sneaker.original_price, old_price)
        else:
            # Live scraper check
            try:
                scraped = await run_scraper(sneaker.url, sneaker.size)
                new_price = scraped["current_price"]
                image = scraped["image"]
                name = scraped["name"]
                
                if new_price < old_price: status = "Dropped"
                elif new_price > old_price: status = "Increased"
                
            except Exception as e:
                print(f"[Worker] Live scraper failed for {sneaker.name}, falling back to simulation: {str(e)}")
                # Fail gracefully into simulation
                new_price, status = simulate_price_update(sneaker.original_price, old_price)
                updates_type = "Simulated Crawler"
                
        # Save updates to database if price has changed
        fields_to_update = {
            "current_price": new_price,
            "status": status,
            "updates_type": updates_type,
            "image": image,
            "name": name,
            "last_checked": datetime.datetime.utcnow()
        }
        
        updated_sneaker = await crud.update_sneaker_fields(db, sneaker_id, fields_to_update)
        
        if old_price != new_price:
            # Add to price history log
            await crud.add_price_history(db, sneaker_id, new_price)
            
            # Check price alert threshold
            if new_price <= sneaker.target_price and new_price < old_price:
                pct_savings = int(((sneaker.original_price - new_price) / sneaker.original_price) * 100)
                alert_msg = (
                    f"🚨 <b>Price Alert!</b>\n\n"
                    f"👟 <b>{sneaker.name}</b> (Size US {sneaker.size}) has dropped to <b>₹{new_price:.2f}</b> "
                    f"(Target: ₹{sneaker.target_price:.2f}) on <b>{sneaker.store}</b>!\n"
                    f"🔥 Saving of <b>{pct_savings}%</b> off retail!\n\n"
                    f"🔗 <a href='{sneaker.url}'>Shop Product Page</a>"
                )
                
                # Write to database notifications
                db_notif = await crud.add_notification(
                    db, 
                    sneaker_id=sneaker.id, 
                    message=f"🔥 Price alert! {sneaker.name} dropped to ₹{new_price:.2f} (Target: ₹{sneaker.target_price:.2f}). Saving of {pct_savings}%!", 
                    old_price=old_price, 
                    new_price=new_price
                )
                
                # Push notifications to channels
                publish_ws_event("NEW_NOTIFICATION", {
                    "id": db_notif.id,
                    "sneaker_id": sneaker_id,
                    "message": db_notif.message,
                    "old_price": old_price,
                    "new_price": new_price,
                    "read": False,
                    "image": image,
                    "created_at": db_notif.created_at.isoformat()
                })
                
                # Send to Telegram bot users
                await send_telegram_alert(alert_msg)
                
        # Broadcast standard sneaker details change to WebSockets
        history_objs = await crud.get_price_history(db, sneaker_id)
        history_list = [{"price": h.price, "timestamp": h.timestamp.isoformat()} for h in history_objs[-10:]]
        
        sneaker_payload = {
            "id": updated_sneaker.id,
            "url": updated_sneaker.url,
            "name": updated_sneaker.name,
            "brand": updated_sneaker.brand,
            "store": updated_sneaker.store,
            "target_price": updated_sneaker.target_price,
            "current_price": updated_sneaker.current_price,
            "original_price": updated_sneaker.original_price,
            "size": updated_sneaker.size,
            "is_active": updated_sneaker.is_active,
            "updates_type": updated_sneaker.updates_type,
            "status": updated_sneaker.status,
            "image": updated_sneaker.image,
            "last_checked": updated_sneaker.last_checked.isoformat(),
            "created_at": updated_sneaker.created_at.isoformat(),
            "history": history_list
        }
        publish_ws_event("SNEAKER_UPDATED", sneaker_payload)

# Celery Tasks

@shared_task(name="app.tasks.check_sneaker_price_task")
def check_sneaker_price_task(sneaker_id: int):
    """Worker task evaluating single sneaker price details"""
    print(f"[Celery] Running price check for sneaker {sneaker_id}")
    run_async(check_sneaker_price_async(sneaker_id))
    return f"Completed price check for sneaker {sneaker_id}"

@shared_task(name="app.tasks.scheduled_scrapes_trigger_task")
def scheduled_scrapes_trigger_task():
    """Worker task finding all active tracked items and queueing checks"""
    async def get_active_ids():
        async with async_session() as db:
            sneakers = await crud.get_sneakers(db)
            return [s.id for s in sneakers if s.is_active]
            
    active_ids = run_async(get_active_ids())
    print(f"[Celery Beat] Dispatched checks for {len(active_ids)} active sneakers")
    for s_id in active_ids:
        check_sneaker_price_task.delay(s_id)
    return f"Dispatched {len(active_ids)} scraping tasks"
