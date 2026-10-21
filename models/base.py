from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class updatetimemixin:
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

class createtimemixin:
    create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
