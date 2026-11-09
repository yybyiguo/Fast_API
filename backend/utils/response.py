from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None):
    content = {"code": 200, "message": message, "data": data}
    # 为了可以将fastapi对象也转为json，没用
    return JSONResponse(jsonable_encoder(content))
