import random
import string
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Link
from app.links.redis_client import schedule_link_deletion
from app.schemas import CustomLinkBase, LinkResponse


async def handle_unauthorized_user(link: CustomLinkBase, db: AsyncSession):
    # Поиск существующей записи без пользователя
    result = await db.execute(
        select(Link).where(
            Link.original_url == link.original_url, Link.user_id.is_(None)
        )
    )
    existing_link = result.scalars().first()

    if existing_link:
        return create_response(existing_link, "Short link already exists!")

    # Генерация нового кода
    short_code = await generate_unique_short_code(db)
    new_link = Link(short_code=short_code, original_url=link.original_url, user_id=None)

    await save_link(db, new_link)
    return create_response(new_link, "Short link created. Register to manage links.")


async def handle_authorized_user(
    user_id: uuid.UUID, link: CustomLinkBase, db: AsyncSession
):
    # Обработка кастомного алиаса
    if link.custom_alias:
        result = await db.execute(
            select(Link).where(Link.short_code == link.custom_alias)
        )
        existing_alias = result.scalars().first()

        if existing_alias:
            await update_expiration(existing_alias, link, db)
            return create_response(existing_alias, "Custom alias already exists!")

        return await create_new_custom_link(user_id, link, db)

    # Поиск существующей ссылки пользователя
    result = await db.execute(
        select(Link).where(
            Link.user_id == user_id, Link.original_url == link.original_url
        )
    )
    existing_link = result.scalars().first()

    if existing_link:
        await update_expiration(existing_link, link, db)
        return create_response(existing_link, "Link already exists!")

    # Создание новой ссылки
    short_code = await generate_unique_short_code(db)
    new_link = Link(
        short_code=short_code, original_url=link.original_url, user_id=user_id
    )
    db.add(new_link)  
    await db.commit()
    await db.refresh(new_link)

    await update_expiration(new_link, link, db)
    await save_link(db, new_link)
    return create_response(new_link, "Short link created!")


def generate_short_code(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


async def generate_unique_short_code(db: AsyncSession):
    while True:
        short_code = generate_short_code()
        result = await db.execute(select(Link).where(Link.short_code == short_code))
        if not result.scalars().first():
            return short_code


async def update_expiration(link: Link, request: CustomLinkBase, db: AsyncSession):
    if not request.expires_at:
        return
    db_link = await db.get(Link, link.id)  # Загружаем объект из базы

    if db_link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    await db.refresh(db_link)  # Обновляем объект
    try:
        expires_at = datetime.strptime(request.expires_at, "%d.%m.%Y %H:%M")
        if expires_at <= datetime.utcnow():
            raise ValueError("Expiration time must be in the future")
        db_link.expires_at = expires_at
        await db.commit()
        await db.refresh(db_link)

        schedule_link_deletion(db_link.short_code, expires_at)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def save_link(db: AsyncSession, link: Link):
    db.add(link)
    await db.commit()
    await db.refresh(link)


def create_response(link: Link, message: str):
    return LinkResponse(
        short_code=link.short_code,
        original_url=link.original_url,
        created_by=link.user_id,
        message=message,
    )


async def create_new_custom_link(
    user_id: uuid.UUID, link: CustomLinkBase, db: AsyncSession
):
    # Создание новой ссылки с кастомным алиасом
    new_link = Link(
        short_code=link.custom_alias, original_url=link.original_url, user_id=user_id
    )

    # Сначала сохраняем ссылку в БД
    await save_link(db, new_link)

    # Теперь можно обновлять expires_at
    await update_expiration(new_link, link, db)

    # Возвращаем ответ
    return create_response(new_link, "Short link with custom alias created!")
