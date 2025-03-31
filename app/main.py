import uvicorn
from fastapi import FastAPI
from app.links.api_links import router as links_router
from app.users.api_users import router as user_router
# from app.links.delete_expired_links import start_scheduler

app = FastAPI()
app.include_router(user_router)
app.include_router(links_router)


# Запускаем удаление устаревших ссылок
# start_scheduler()

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True, host="0.0.0.0", log_level="info")

# uvicorn app.main:app --reload
# sudo systemctl start redis

