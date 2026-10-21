# from models.base import Base

# # 必须导入所有模型模块，模型类继承 Base 时才会把表注册到 Base.metadata
# import models.user
# import models.news
# import models.favorite
# import models.history

# print(Base.metadata.tables.keys())  # 应该看到全部表名
# print(Base.metadata)  # 打印 metadata 对象

# from models.user import UserToken

# print(
#     UserToken.__table__.c.expires_at.type
# )  # 应该是 DateTime()，不是 String(length=50)

# test_gender.py
from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


print(list(Gender))
print(Gender.male.value)
print(Gender("male"))
