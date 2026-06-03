import datetime
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

# Price History Schemas
class PriceHistoryBase(BaseModel):
    price: float
    timestamp: datetime.datetime

class PriceHistoryCreate(PriceHistoryBase):
    pass

class PriceHistoryResponse(PriceHistoryBase):
    id: int
    sneaker_id: int

    class Config:
        from_attributes = True

# Notification Schemas
class NotificationBase(BaseModel):
    sneaker_id: int
    message: str
    old_price: float
    new_price: float
    read: bool
    created_at: datetime.datetime

class NotificationResponse(BaseModel):
    id: int
    sneaker_id: int
    message: str
    old_price: float
    new_price: float
    read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Sneaker Schemas
class SneakerCreate(BaseModel):
    url: str = Field(..., description="The sneaker product page URL")
    size: str = Field("9.5", description="The target US shoe size to watch")
    target_price: Optional[float] = Field(None, description="Notify when price drops to or below this threshold")

class SneakerUpdate(BaseModel):
    target_price: Optional[float] = None
    is_active: Optional[bool] = None

class SneakerResponse(BaseModel):
    id: int
    url: str
    name: str
    brand: str
    store: str
    target_price: float
    current_price: float
    original_price: float
    size: str
    is_active: bool
    updates_type: str
    status: str
    last_checked: datetime.datetime
    created_at: datetime.datetime
    history: List[PriceHistoryBase] = []

    class Config:
        from_attributes = True

# Telegram User Schemas
class TelegramUserCreate(BaseModel):
    chat_id: str

class TelegramUserResponse(BaseModel):
    id: int
    chat_id: str
    is_active: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True
