from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class updatetimemixin:
    update_time: Mapped[datetime] = mapped_column(
        DateTime, onupdate=func.now(),server_default=func.now()
    )

class createtimemixin:
    create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
