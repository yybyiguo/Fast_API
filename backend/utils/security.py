from passlib.context import CryptContext

# 创建密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 加密
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)
