import time
from datetime import datetime
import redis


# Подключение к Redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


def schedule_link_deletion(short_code, expires_at):
    """
    Запланировать удаление ссылки по истечении срока.
    """

    if isinstance(expires_at, datetime):
        expires_at_timestamp = int(expires_at.timestamp())  # Переводим в Unix-время
    else:
        expires_at_timestamp = int(
            datetime.strptime(expires_at, "%d.%m.%Y %H:%M").timestamp()
        )

    ttl = expires_at_timestamp - int(time.time())  # Определяем TTL в секундах

    if ttl > 0:
        redis_client.setex(short_code, ttl, "expired")  # Устанавливаем TTL правильно
        print(
            f"Запланировано удаление для {short_code} через {ttl} сек (в {expires_at})"
        )
    else:
        print(f"Ошибка: указанное время {expires_at} уже прошло")


def get_expired_links():
    """
    Проверяет все ссылки на истечение срока действия в Redis.
    """
    expired_links = []
    all_links = redis_client.keys("*")  # Получаем все ключи

    for link in all_links:
        ttl = redis_client.ttl(link)  # Время жизни ключа

        print(f"Ссылка {link} TTL: {ttl}")  # Для отладки

        if ttl is None or ttl == -2:  # Ключ уже удалён
            expired_links.append(link)
        elif ttl == -1:  # Ключ без TTL, значит, его не надо удалять
            continue
        elif ttl == 0:  # Срок жизни закончился
            expired_links.append(link)

    return expired_links
