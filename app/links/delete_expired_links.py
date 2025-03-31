import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_async_session
from app.database.models import Link
from app.links.redis_client import get_expired_links


async def delete_expired_links():
    """
    Удаляет устаревшие ссылки из БД.
    """
    async for db in get_async_session():
        expired_links = get_expired_links()
        if not expired_links:
            print("Нет истекших ссылок.")  # Отладка
            return

        print(f"Удаление ссылок из БД: {expired_links}")  # Отладка
        await db.execute(delete(Link).where(Link.short_code.in_(expired_links)))
        await db.commit()
        print(f"Удалены устаревшие ссылки: {expired_links}")


def start_scheduler():
    """
    Запускает планировщик задач для удаления устаревших ссылок.
    """
    print("Запуск планировщика задач...")

    loop = asyncio.get_event_loop()  # Получаем текущий event loop
    scheduler = BackgroundScheduler()

    def run_async_task():
        asyncio.run_coroutine_threadsafe(delete_expired_links(), loop)

    scheduler.add_job(
        run_async_task,
        "interval",
        minutes=1,
        id="delete_expired_links",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,  
    )

    scheduler.start()
    print("Планировщик запущен.")
    print(f"Задача удаления: {scheduler.get_job('delete_expired_links')}")
