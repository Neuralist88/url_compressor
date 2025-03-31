from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.database import get_async_session
from app.database.models import User
from app.schemas import UserCreate
from app.users.auth import create_access_token, get_password_hash, verify_password


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_async_session)):
    """
    Функция для регистрации пользователя
    """
    # Проверка, существует ли пользователь
    result = await db.execute(select(User).where(User.email == user.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Хешируем пароль и сохраняем
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, password=hashed_password)
    db.add(new_user)
    await db.commit()
    return {"message": "User registered successfully"}


# Маршрут для аутентификации пользователя.
# Если данные правильные, возвращается JWT токен.
@router.post("/login")
async def login(user: UserCreate, db: AsyncSession = Depends(get_async_session)):
    """
    Функция для авторизации пользователя
    """
    result = await db.execute(select(User).where(User.email == user.email))
    existing_user = result.scalars().first()
    if not existing_user or not verify_password(user.password, existing_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Создаем JWT токен
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(existing_user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
