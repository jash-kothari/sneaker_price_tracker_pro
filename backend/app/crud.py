from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, desc
from app import models, schemas
import datetime

# Sneakers CRUD
async def get_sneakers(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(models.Sneaker)
        .offset(skip)
        .limit(limit)
        .order_by(models.Sneaker.id.desc())
    )
    return result.scalars().all()

async def get_sneaker(db: AsyncSession, sneaker_id: int):
    result = await db.execute(
        select(models.Sneaker).filter(models.Sneaker.id == sneaker_id)
    )
    return result.scalar_one_or_none()

async def get_sneaker_by_url(db: AsyncSession, url: str):
    result = await db.execute(
        select(models.Sneaker).filter(models.Sneaker.url == url)
    )
    return result.scalar_one_or_none()

async def create_sneaker(db: AsyncSession, sneaker_details: dict):
    db_sneaker = models.Sneaker(**sneaker_details)
    db.add(db_sneaker)
    await db.commit()
    await db.refresh(db_sneaker)
    return db_sneaker

async def update_sneaker(db: AsyncSession, sneaker_id: int, updates: schemas.SneakerUpdate):
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return await get_sneaker(db, sneaker_id)
        
    await db.execute(
        update(models.Sneaker)
        .where(models.Sneaker.id == sneaker_id)
        .values(**update_data)
    )
    await db.commit()
    return await get_sneaker(db, sneaker_id)

async def update_sneaker_fields(db: AsyncSession, sneaker_id: int, fields: dict):
    await db.execute(
        update(models.Sneaker)
        .where(models.Sneaker.id == sneaker_id)
        .values(**fields)
    )
    await db.commit()
    return await get_sneaker(db, sneaker_id)

async def delete_sneaker(db: AsyncSession, sneaker_id: int):
    result = await db.execute(
        delete(models.Sneaker).where(models.Sneaker.id == sneaker_id)
    )
    await db.commit()
    return result.rowcount > 0

# Price History CRUD
async def get_price_history(db: AsyncSession, sneaker_id: int, limit: int = 100):
    result = await db.execute(
        select(models.PriceHistory)
        .filter(models.PriceHistory.sneaker_id == sneaker_id)
        .order_by(models.PriceHistory.timestamp.asc())
        .limit(limit)
    )
    return result.scalars().all()

async def add_price_history(db: AsyncSession, sneaker_id: int, price: float, timestamp: datetime.datetime = None):
    db_history = models.PriceHistory(
        sneaker_id=sneaker_id,
        price=price,
        timestamp=timestamp or datetime.datetime.utcnow()
    )
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history

# Notifications CRUD
async def get_notifications(db: AsyncSession, limit: int = 50):
    result = await db.execute(
        select(models.Notification)
        .order_by(desc(models.Notification.created_at))
        .limit(limit)
    )
    return result.scalars().all()

async def add_notification(db: AsyncSession, sneaker_id: int, message: str, old_price: float, new_price: float):
    db_notification = models.Notification(
        sneaker_id=sneaker_id,
        message=message,
        old_price=old_price,
        new_price=new_price,
        read=False
    )
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification

async def mark_notifications_read(db: AsyncSession):
    await db.execute(
        update(models.Notification)
        .where(models.Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return True

# Telegram Users CRUD
async def get_telegram_users(db: AsyncSession):
    result = await db.execute(select(models.TelegramUser).filter(models.TelegramUser.is_active == True))
    return result.scalars().all()

async def get_telegram_user(db: AsyncSession, chat_id: str):
    result = await db.execute(select(models.TelegramUser).filter(models.TelegramUser.chat_id == chat_id))
    return result.scalar_one_or_none()

async def register_telegram_user(db: AsyncSession, chat_id: str):
    db_user = await get_telegram_user(db, chat_id)
    if db_user:
        if not db_user.is_active:
            db_user.is_active = True
            await db.commit()
            await db.refresh(db_user)
        return db_user
        
    db_user = models.TelegramUser(chat_id=chat_id, is_active=True)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def deactivate_telegram_user(db: AsyncSession, chat_id: str):
    db_user = await get_telegram_user(db, chat_id)
    if db_user:
        db_user.is_active = False
        await db.commit()
        return True
    return False
