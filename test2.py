from datetime import datetime
from decimal import Decimal
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, HTTPException,Request
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field
from sqlalchemy import func, DateTime, String, DECIMAL, select,delete
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# 配置类：定义所有环境变量
class Settings(BaseSettings):
    # 数据库配置
    db_host: str
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str

    # jwt配置示例
    jwt_secret: str
    jwt_expire_minutes: int = 30

    # 读取 .env 文件
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# lru_cache 缓存，全局只实例化一次，性能更好
@lru_cache()
def get_settings():
    return Settings()
settings = get_settings()

DB_URL = (
    f"mysql+aiomysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
)
#创建连接池
async_engine = create_async_engine(DB_URL, echo=True, pool_size=10, max_overflow=20)
#会话工厂，被使用时会自动向连接池请求一条连接，session是在数据库连接之上的一层
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    __abstract__ = True
    create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    update_time: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

class BookIn(BaseModel):
    title: str = Field(..., max_length=255)
    author: str = Field(..., max_length=255)
    price: Decimal = Field(..., gt=0)

class BookOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    title: str
    author: str
    price: Decimal
    create_time: datetime
    update_time: datetime

#先创建连接池再创建表，都在startup中完成
async def create_table():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建成功！")

#装饰器快速创建异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_table()
    yield
    await async_engine.dispose()
    print("✅ 数据库连接已关闭")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,       # 允许携带 cookie
    allow_methods=["*"],          # 允许的请求方法
    allow_headers=["*"],          # 允许的请求头
)

#从会话工厂中创建一次会话实例
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# 全局捕获HTTPException，重写返回格式
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        content={
            "code": exc.status_code,
            "msg": exc.detail,
            "data": None
        }
    )

@app.get("/")
async def root():
    return {
            "code": 200,
            "msg": "fastapi响应成功",
        }

@app.post("/add_books")
async def add_books(book_in: list[BookIn], db: AsyncSession = Depends(get_db)):
    books = [Book(**i.model_dump()) for i in book_in]
    try:
        db.add_all(books)
        await db.commit()
        print(f"新增{len(book_in)}条数据成功")
        for i in books:
            await db.refresh(i)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {
            "code": 200,
            "msg": "增加成功",
            "data": {
                "books": books
            }
        }

class delete_object(BaseModel):
    id: int | None = Field(None, gt=0)
    title: str | None = Field(None, max_length=255)
    author: str | None = Field(None, max_length=255)
    price: Decimal | None = Field(None, gt=0)

@app.delete("/delete_books")
async def delete_books(
    in_del_books: list[delete_object],
    db: AsyncSession = Depends(get_db),
):
    count=0
    print(in_del_books)
    try:
        for i in in_del_books:
            stmt = delete(Book)
            if i.id is not None:
                stmt = stmt.where(Book.id == i.id)
            elif i.title is not None:
                stmt = stmt.where(Book.title == i.title)
            elif i.author is not None:
                stmt = stmt.where(Book.author == i.author)
            elif i.price is not None:
                stmt = stmt.where(Book.price == i.price)
            else:
                print("这个对象所有字段都是 None，跳过")
                continue   # 没有任何条件，跳过

            result = await db.execute(stmt)
            count = count + result.rowcount
            print(f"条件 {i} 删除了 {result.rowcount} 条")

        await db.commit()
        return {
            "code": 200,
            "msg": "删除成功",
            "data": {
                "delete_count": count
            }
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/update_books/{book_id}")
async def update_books(book_id:int,data: BookIn, db: AsyncSession = Depends(get_db)):
    book=await db.get(Book ,book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    else:
        book.title=data.title
        book.author=data.author
        book.price=data.price
    try:
        await db.commit()
        await db.refresh(book)
        print(f"更新book表成功，id={book_id}")
        return {
            "code": 200,
            "msg": "更新成功",
            "data": {
                "book": book
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/books")
async def get_books(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book))
    return {
            "code": 200,
            "msg": "请求成功",
            "data": {
                "result":result.scalars().all()
            }
        }
