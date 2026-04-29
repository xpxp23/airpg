from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        to_encode = {"sub": user_id, "exp": expire}
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def decode_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload.get("sub")
        except JWTError:
            return None

    async def register(self, data: UserRegister) -> Token:
        # Check if email exists
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Check if username exists
        existing = await self.db.execute(select(User).where(User.username == data.username))
        if existing.scalar_one_or_none():
            raise ValueError("Username already taken")

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=self.hash_password(data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        token = self.create_access_token(user.id)
        return Token(
            access_token=token,
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar_url=user.avatar_url,
                created_at=user.created_at.isoformat(),
            ),
        )

    async def login(self, data: UserLogin) -> Token:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not self.verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        token = self.create_access_token(user.id)
        return Token(
            access_token=token,
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                avatar_url=user.avatar_url,
                created_at=user.created_at.isoformat(),
            ),
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
