### Описание API
![image](https://github.com/user-attachments/assets/03390087-4d5b-48fe-ac4e-08408b97298e)

- **POST /users/register**
  Регистрация нового пользователя по email и password
  Параметры запроса:\
```{
  "email": "string",  
  "password": "string"
}
```

- **POST /users/login**
  Параметры запроса:\
  Авторизация пользователя\
```
{
  "email": "string",  
  "password": "string"
}
```

Ответ: JWT токен (действителен в течение 30 мин)

- **POST /links/shorten**
  Получение короткой ссылки (8 символов) по длинной ссылке
  Параметры запроса:\
```
{
 "original_url": "string",
 "custom_alias": "string", # опционально. Применяется только для авторизованных пользователей)
 "expires_at": "string" # опционально. Применяется только для авторизованных пользователей)
}
```

Ответ
```
{
 "short_code": link.short_code,
 "original_url": link.original_url,
 "created_by": link.user_id,
 "message": message,
}
```

- **GET /links/{short_code}**
  Перенаправление на оригинальную длинную ссылку по короткой ссылке\
  Возвращает страницу, расположенную по оригинальному url, увеличивает счетчик ссылок на 1

- **DELETE /links/{short_code}**
  Удаление записи из БД по короткой ссылке (досутпно только для авторизованных пользователей)\

- **PUT /links/{short_code}**
  Переопределение original_url, соответствующее переданному short_code (досутпно только для авторизованных пользователей)\

- **GET /links/{short_code}/stats**
  Получение статистики по short_code (досутпно только для авторизованных пользователей)\

  Ответ
```
{
 "original_url": link.original_url,
 "created_by": link.created_by,
 "click_count": link.click_count,
 "last_used_at": link.last_used_at,
}
```
  
- **GET /links/search?original_url={url}**
  Получение short_code по original_url

 
### Примеры запросов 
Примеры запросов и демонстрация работы эндпоинтов на [видео](https://youtu.be/GAn09xg9pXY)


### База данных
В приложении использовалая БД PostgreSQL

структура базы данных:
```
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    links = relationship("Link", back_populates="user")


class Link(Base):
    __tablename__ = "links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code = Column(String(10), unique=True, nullable=False, index=True)
    original_url = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    click_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_used_at = Column(TIMESTAMP, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)

    user = relationship("User", back_populates="links")
```
