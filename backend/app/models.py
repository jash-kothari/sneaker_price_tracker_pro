import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Sneaker(Base):
  __tablename__ = "sneakers"

  id = Column(Integer, primary_key=True, index=True)
  url = Column(String, unique=True, index=True, nullable=False)
  name = Column(String, nullable=False)
  brand = Column(String, nullable=False)
  store = Column(String, nullable=False)
  target_price = Column(Float, nullable=False)
  current_price = Column(Float, nullable=False)
  original_price = Column(Float, nullable=False)
  size = Column(String, nullable=False)
  is_active = Column(Boolean, default=True, nullable=False)
  updates_type = Column(String, default="Simulated Crawler", nullable=False)
  status = Column(String, default="Stable", nullable=False)
  image = Column(String, nullable=True)
  last_checked = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

  # Relationships
  history = relationship("PriceHistory", back_populates="sneaker", cascade="all, delete-orphan")
  notifications = relationship("Notification", back_populates="sneaker", cascade="all, delete-orphan")


class PriceHistory(Base):
  __tablename__ = "price_history"

  id = Column(Integer, primary_key=True, index=True)
  sneaker_id = Column(Integer, ForeignKey("sneakers.id", ondelete="CASCADE"), nullable=False)
  price = Column(Float, nullable=False)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

  # Relationships
  sneaker = relationship("Sneaker", back_populates="history")


class Notification(Base):
  __tablename__ = "notifications"

  id = Column(Integer, primary_key=True, index=True)
  sneaker_id = Column(Integer, ForeignKey("sneakers.id", ondelete="CASCADE"), nullable=False)
  message = Column(String, nullable=False)
  old_price = Column(Float, nullable=False)
  new_price = Column(Float, nullable=False)
  read = Column(Boolean, default=False, nullable=False)
  created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

  # Relationships
  sneaker = relationship("Sneaker", back_populates="notifications")


class TelegramUser(Base):
  __tablename__ = "telegram_users"

  id = Column(Integer, primary_key=True, index=True)
  chat_id = Column(String, unique=True, index=True, nullable=False)
  is_active = Column(Boolean, default=True, nullable=False)
  created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
