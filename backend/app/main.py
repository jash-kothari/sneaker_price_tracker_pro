import asyncio
import json
import datetime
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as async_redis

from app import crud, schemas, models
from app.database import get_db, engine, Base, async_session
from app.config import settings
from app.scrapers import run_scraper
from app.scrapers.base import BaseScraper
from app.tasks import check_sneaker_price_task

# Store active web clients
active_websockets = set()

async def redis_pubsub_listener():
    """Async thread listening to Redis Pub/Sub channel and relaying events to WebSockets"""
    r_client = async_redis.from_url(settings.REDIS_URL)
    pubsub = r_client.pubsub()
    await pubsub.subscribe("solesentry_updates")
    print("[WS Relay] Connected to Redis Pub/Sub. Listening for updates...")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message:
                data = message["data"].decode("utf-8")
                # Relay to all connected sockets
                dead_sockets = []
                for ws in list(active_websockets):
                    try:
                        await ws.send_text(data)
                    except Exception:
                        dead_sockets.append(ws)
                for dead in dead_sockets:
                    active_websockets.discard(dead)
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        print("[WS Relay] Listener task cancelled.")
    except Exception as e:
        print(f"[WS Relay] Error in Redis Pub/Sub listener: {str(e)}")
    finally:
        await pubsub.unsubscribe("solesentry_updates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    # 1. Create database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Seed initial demo data if empty
    async with async_session() as db:
        await seed_demo_data(db)
        
    # 3. Start Redis Pub/Sub listener in background
    listener_task = asyncio.create_task(redis_pubsub_listener())
    
    yield
    
    # Shutdown tasks
    listener_task.cancel()
    await listener_task

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Allow CORS for React development dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to React origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def seed_demo_data(db: AsyncSession):
    sneakers = await crud.get_sneakers(db)
    if len(sneakers) > 0:
        return
        
    print("[Database] Seeding initial mock sneakers...")
    demo_items = [
        {
            "url": "https://www.nike.com/in/t/air-jordan-1-retro-high-og-shoes-dz5485-612",
            "size": "10",
            "target_price": 15000.00
        },
        {
            "url": "https://www.vegnonveg.com/products/nike-dunk-low-retro-white-black-2021",
            "size": "9.5",
            "target_price": 8000.00
        },
        {
            "url": "https://www.superkicks.in/products/adidas-ultraboost-1-0-hq4183",
            "size": "11",
            "target_price": 11000.00
        }
    ]
    
    for item in demo_items:
        # Create base details
        scraper = BaseScraper(item["url"], item["size"])
        orig_p = scraper.generate_mock_price()
        
        # Hardcode initial states for realistic dashboard view in INR
        if "jordan" in scraper.slug:
            curr_p = 14500.00 # dropped below 15000 target
            status = "Dropped"
        elif "dunk" in scraper.slug:
            curr_p = 9495.00 # stable
            status = "Stable"
        else:
            curr_p = 11999.00 # increased from 10999
            status = "Increased"
            
        details = {
            "url": item["url"],
            "name": scraper.name,
            "brand": scraper.brand,
            "store": scraper.store,
            "size": item["size"],
            "target_price": item["target_price"],
            "original_price": orig_p,
            "current_price": curr_p,
            "updates_type": "Simulated Crawler",
            "status": status,
            "is_active": True,
            "last_checked": datetime.datetime.utcnow(),
            "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=10)
        }
        
        db_sneaker = await crud.create_sneaker(db, details)
        
        # Seed 10 days of price history
        now = datetime.datetime.utcnow()
        last_p = curr_p + 1000.0
        for i in range(10, -1, -1):
            timestamp = now - datetime.timedelta(days=i)
            if i > 0:
                change = random_percent_change()
                last_p = round(last_p * (1 + change), 2)
            else:
                last_p = curr_p
            await crud.add_price_history(db, db_sneaker.id, last_p, timestamp)
            
        # Add a demo notification in INR
        if "jordan" in scraper.slug:
            await crud.add_notification(
                db,
                sneaker_id=db_sneaker.id,
                message=f"🔥 Price alert! {db_sneaker.name} dropped to ₹14,500.00 (Target: ₹15,000.00). Saving of 14%!",
                old_price=16000.00,
                new_price=14500.00
            )

def random_percent_change():
    import random
    return random.uniform(-0.04, 0.04)


# --- REST ROUTES ---

def make_sneaker_response(s, history_list) -> schemas.SneakerResponse:
    return schemas.SneakerResponse(
        id=s.id,
        url=s.url,
        name=s.name,
        brand=s.brand,
        store=s.store,
        target_price=s.target_price,
        current_price=s.current_price,
        original_price=s.original_price,
        size=s.size,
        is_active=s.is_active,
        updates_type=s.updates_type,
        status=s.status,
        last_checked=s.last_checked,
        created_at=s.created_at,
        history=history_list
    )

@app.get("/api/sneakers", response_model=List[schemas.SneakerResponse])
async def read_sneakers(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    sneakers = await crud.get_sneakers(db, skip=skip, limit=limit)
    response_payload = []
    
    for s in sneakers:
        history = await crud.get_price_history(db, s.id, limit=10)
        history_list = [{"price": h.price, "timestamp": h.timestamp} for h in history]
        
        s_dict = make_sneaker_response(s, history_list)
        response_payload.append(s_dict)
        
    return response_payload

@app.get("/api/sneakers/{sneaker_id}/history", response_model=List[schemas.PriceHistoryResponse])
async def read_sneaker_history(sneaker_id: int, db: AsyncSession = Depends(get_db)):
    history = await crud.get_price_history(db, sneaker_id)
    return history

@app.post("/api/sneakers", response_model=schemas.SneakerResponse, status_code=201)
async def track_sneaker(payload: schemas.SneakerCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Check if URL already tracked
    existing = await crud.get_sneaker_by_url(db, payload.url)
    if existing:
        raise HTTPException(status_code=400, detail="Sneaker is already being tracked")
        
    try:
        # Run synchronous metadata parser
        scraper = BaseScraper(payload.url, payload.size)
        orig_price = scraper.generate_mock_price()
        
        target = payload.target_price if payload.target_price is not None else round(orig_price * 0.9, 2)
        
        details = {
            "url": payload.url,
            "name": scraper.name,
            "brand": scraper.brand,
            "store": scraper.store,
            "size": payload.size,
            "target_price": target,
            "original_price": orig_price,
            "current_price": orig_price,
            "updates_type": "Simulated Crawler", # Initial state
            "status": "Stable",
            "is_active": True,
            "last_checked": datetime.datetime.utcnow(),
            "created_at": datetime.datetime.utcnow()
        }
        
        # Save Sneaker
        db_sneaker = await crud.create_sneaker(db, details)
        
        # Generate and save price history seed
        now = datetime.datetime.utcnow()
        last_p = orig_price
        for i in range(10, 0, -1):
            timestamp = now - datetime.timedelta(days=i)
            change = random_percent_change()
            last_p = round(last_p * (1 + change), 2)
            await crud.add_price_history(db, db_sneaker.id, last_p, timestamp)
            
        # Add current price history point
        await crud.add_price_history(db, db_sneaker.id, orig_price, now)
        
        # Dispatch background scrape task to run immediately via Celery
        background_tasks.add_task(check_sneaker_price_task.delay, db_sneaker.id)
        
        # Query final object with history
        history = await crud.get_price_history(db, db_sneaker.id, limit=10)
        history_list = [{"price": h.price, "timestamp": h.timestamp} for h in history]
        
        return make_sneaker_response(db_sneaker, history_list)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track sneaker: {str(e)}")

@app.put("/api/sneakers/{sneaker_id}", response_model=schemas.SneakerResponse)
async def edit_sneaker(sneaker_id: int, updates: schemas.SneakerUpdate, db: AsyncSession = Depends(get_db)):
    db_sneaker = await crud.get_sneaker(db, sneaker_id)
    if not db_sneaker:
        raise HTTPException(status_code=404, detail="Sneaker not found")
        
    updated = await crud.update_sneaker(db, sneaker_id, updates)
    history = await crud.get_price_history(db, updated.id, limit=10)
    history_list = [{"price": h.price, "timestamp": h.timestamp} for h in history]
    
    return make_sneaker_response(updated, history_list)

@app.delete("/api/sneakers/{sneaker_id}")
async def stop_tracking(sneaker_id: int, db: AsyncSession = Depends(get_db)):
    db_sneaker = await crud.get_sneaker(db, sneaker_id)
    if not db_sneaker:
        raise HTTPException(status_code=404, detail="Sneaker not found")
        
    deleted = await crud.delete_sneaker(db, sneaker_id)
    return {"success": deleted}

@app.post("/api/sneakers/{sneaker_id}/check")
async def force_price_check(sneaker_id: int, db: AsyncSession = Depends(get_db)):
    db_sneaker = await crud.get_sneaker(db, sneaker_id)
    if not db_sneaker:
        raise HTTPException(status_code=404, detail="Sneaker not found")
        
    # Queue immediate check in Celery
    check_sneaker_price_task.delay(sneaker_id)
    return {"message": "Scrape task dispatched successfully"}

@app.get("/api/notifications", response_model=List[schemas.NotificationResponse])
async def read_notifications(db: AsyncSession = Depends(get_db)):
    notifications = await crud.get_notifications(db)
    return notifications

@app.post("/api/notifications/read")
async def read_all_notifications(db: AsyncSession = Depends(get_db)):
    success = await crud.mark_notifications_read(db)
    return {"success": success}

@app.post("/api/telegram/users", response_model=schemas.TelegramUserResponse)
async def register_tg_user(payload: schemas.TelegramUserCreate, db: AsyncSession = Depends(get_db)):
    user = await crud.register_telegram_user(db, payload.chat_id)
    return user

@app.delete("/api/telegram/users/{chat_id}")
async def untrack_tg_user(chat_id: str, db: AsyncSession = Depends(get_db)):
    deactivated = await crud.deactivate_telegram_user(db, chat_id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="Telegram user not found")
    return {"success": True}


# --- WEBSOCKET ROUTE ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    print(f"[WS] Client connected. Total sockets active: {len(active_websockets)}")
    
    try:
        while True:
            # Keep socket alive and respond to client-sent text if any
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
        print(f"[WS] Client disconnected. Sockets active: {len(active_websockets)}")
    except Exception as e:
        active_websockets.discard(websocket)
        print(f"[WS] WebSocket error: {str(e)}")
