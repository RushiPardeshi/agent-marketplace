from sqlalchemy import Integer, String, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from src.db import Base
from datetime import datetime

class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    seller_min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )