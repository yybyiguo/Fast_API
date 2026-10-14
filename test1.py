#uvicorn main:app --reload

from fastapi import FastAPI,Path,Query, HTTPException,Depends
from pydantic import BaseModel,Field
from starlette.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

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

@app.add_middleware('http')

@app.get("/")
async def root():
    return {"message": "Hello World"}
#路径参数
@app.get("/hello/{name}")
async def hello(name: str):
    return {"message": f"Hello {name}",'name':name}

@app.get("/author/{name}")
async def hello(name: str=Path(...,min_length=2,max_length=20,description="查找书的作者")):
    return {"message": f"这是作者{name}的信息",'author':name}
#查询参数
@app.get("/news/news_list")
async def gets_news_list(skip: int=Query(1,gt=0,lt=10),limit: int=Query(10,gt=0,lt=100)):
    return {"msg":f"跳过{skip},限制{limit}个"}

#请求体参数
class Book(BaseModel):
    title: str=Field(...,min_length=1,max_length=20)
    author: str=Field(...,min_length=2,max_length=20)
    id:int=Field(...,gt=0,lt=100)
@app.post("/book")
async def add_book(book:Book):
    return {'status':'添加成功','编号':book.id,'作者':book.author,'书名':book.title}

#响应类型 html
@app.get("/html")
async def get_html():
    return HTMLResponse("<h1>ni hao</h1><h3>bu hao</h3>")
#或者
# @app.get("/html",response_class=HTMLResponse)
# async def get_html():
#     return "<h1>ni hao</h1><h3>bu hao</h3>"
#响应类型 file
@app.get("/file",response_class=FileResponse)
async def get_file():
    path='./file/p1.jpg'
    return path
#自定义响应类型
#写一个class，@app.get("/file",response_class=类名)
#return 后面的格式就必须要是class了，不然就报错

#异常响应处理  raise HTTPException(status_code=404,detail='')
@app.get("/news/{news_id}")
async def get_id(news_id:int):
    list1=[1,2,3,4,5]
    if news_id not in list1:
        raise HTTPException(status_code=404,detail='不存在')
    return {'id':news_id}

#中间件（从下至上运行）
@app.middleware("http")
async def middleware(request,call_next):
    response= await call_next(request)
    return response

#依赖
#先写依赖项
async def common_parameters(skip:int,limit:int):
    return {"skip":skip,"limit":limit}
#注入依赖
# @app.get("/news/news_list")
# async def gets_news_list(skip: int=Query(1,gt=0,lt=10),limit: int=Query(10,gt=0,lt=100)):
#     return {"msg":f"跳过{skip},限制{limit}个"}
#                      ||
# async def get_common_parameters(commons=Depends(common_parameters)):
#     return commons















