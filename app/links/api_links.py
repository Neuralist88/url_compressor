import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_async_session
from app.database.models import Link
from app.links.functions import handle_authorized_user, handle_unauthorized_user
from app.schemas import CustomLinkBase, LinkBase, LinkResponse
from app.users.auth import get_current_user, verify_jwt_token
import logging



router = APIRouter(prefix="/links", tags=["links"])


@router.post("/shorten", response_model=LinkResponse)
async def create_short_link(
    link: CustomLinkBase,
    request: Request,
    db: AsyncSession = Depends(get_async_session)):
    """
    Функция для создания короткой ссылки.
    Для авторизованных пользователей есть возможность задать
    свой алиас и время жизни ссылки
    """
    user_id = None
    auth_header = request.headers.get("Authorization")

    # Проверка авторизации
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = verify_jwt_token(token)
            user_id = uuid.UUID(payload.get("sub"))
        except Exception:
            pass  # Если неверный токен, значит, просто считаем пользователя неавторизованным

    # Обработка запроса неавторизованных пользователей
    if not user_id:
        return await handle_unauthorized_user(link, db)

    # Обработка запроса авторизованных пользователей
    return await handle_authorized_user(user_id, link, db)


@router.get("/search")
async def search_link(
    original_url: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Функция поиска short_code по оригинальному URL.
    - Если пользователь авторизован, ищем только его ссылки.
    - Если неавторизован, ищем только ссылки с user_id = NULL.
    """
    user_id = None
    auth_header = request.headers.get("Authorization")

    # Проверка авторизации пользователя
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = verify_jwt_token(token)
            user_id = uuid.UUID(payload.get("sub"))
        except Exception:
            pass  # Если токен неверный, оставляем user_id = None

    # Формируем SQL-запрос с учетом user_id
    query = select(Link).where(Link.original_url == original_url)

    if user_id:
        query = query.where(Link.user_id == user_id)  # Ищем среди ссылок пользователя
    else:
        query = query.where(Link.user_id.is_(None))  # Ищем ссылки без владельца

    result = await db.execute(query)
    links = result.scalars().all()
    
    if not links:
        raise HTTPException(status_code=404, detail="Short links not found")

    return [{"short_code": link.short_code} for link in links]


@router.get("/{short_code}", status_code=307)
async def redirect_to_original(
    short_code: str,
    db: AsyncSession = Depends(get_async_session)):
    """
    Функция перенаправления по короткой ссылки на оргинальный url
    """
    # Получаем ссылку из БД
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalars().first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Обновляем поля: click_count, last_used_at, expires_at
    await db.execute(
        update(Link)
        .where(Link.id == link.id)
        .values(click_count=link.click_count + 1, last_used_at=datetime.utcnow())
    )
    await db.commit()

    # Проверяем протокол и исправляем при необходимости
    if not link.original_url.startswith(("http://", "https://")):
        link.original_url = "https://" + link.original_url

    # Выполняем редирект на оригинальный URL
    return RedirectResponse(url=link.original_url, status_code=307)


@router.delete("/{short_code}", status_code=status.HTTP_200_OK)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_async_session),
    current_user_id: str = Depends(
        get_current_user)):
    """
    Функция для удаления ссылки из БД (только для авторизованных пользователей)
    """
    # Ищем ссылку в базе данных по short_code
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalars().first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем, что ссылка была создана текущим пользователем
    if str(link.user_id) != current_user_id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to delete this link"
        )

    # Удаляем ссылку из базы данных
    await db.delete(link)
    await db.commit()

    return {"message": "Link deleted successfully"}


@router.put("/{short_code}", status_code=status.HTTP_200_OK)
async def update_link(
    short_code: str,
    new_link: LinkBase,
    db: AsyncSession = Depends(get_async_session),
    current_user_id: str = Depends(get_current_user)):
    """
    Функция для обновления короткой ссылки (только для авторизованных пользователей)
    """
    # Проверка существования ссылки
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalars().first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        )

    # Проверяем, что ссылка была создана текущим пользователем
    if str(link.user_id) != current_user_id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to change this link"
        )

    # Обновление ссылки
    link.original_url = new_link.original_url
    db.add(link)
    await db.commit()

    return {"message": "Link updated successfully"}


@router.get("/{short_code}/stats")
async def get_link_stats(
    short_code: str,
    db: AsyncSession = Depends(get_async_session),
    current_user_id: str = Depends(get_current_user)):
    """
    Функция для получения статистики ссылки (только для авторизованных пользователей)
    """
    # Выполняем запрос для поиска ссылки
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalars().first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем, что ссылка была создана текущим пользователем
    if str(link.user_id) != current_user_id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to change this link"
        )

    # Возвращаем статистику ссылки
    return {
        "original_url": link.original_url,
        "created_at": link.created_at,
        "click_count": link.click_count,
        "last_used_at": link.last_used_at,
    }
