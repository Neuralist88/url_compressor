import uuid
from typing import Optional
from pydantic import BaseModel


# Модель данных для регистрации пользователя
class UserCreate(BaseModel):
    email: str
    password: str


# Ответ при авторизации
class Token(BaseModel):
    access_token: str
    token_type: str


# Создание ссылки
class LinkBase(BaseModel):
    original_url: str


# Создание ссылки с пользовательским алиасом
class CustomLinkBase(LinkBase):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[str] = None


# Модель для возвращаемого результата
class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    created_by: Optional[uuid]
    message: Optional[str]

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
