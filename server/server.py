import sys
import json
import uvicorn
import logging
import traceback
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Query, Body, HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any

from database import db

app = FastAPI(title="AI Issue Genius API", version="1.0.0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# Настройки JWT
SECRET_KEY = "your-secret-key-change-in-production"  # Замените в продакшене!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Схемы безопасности
security = HTTPBearer()

# Pydantic модели
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    is_active: bool


# Вспомогательные функции
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получает текущего пользователя из JWT токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

    user = await db.get_user_by_email(token_data.email)
    if user is None:
        raise credentials_exception

    return user


# Обработчики событий запуска и остановки
# Обработчики событий запуска и остановки
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    await db.connect()
    print("Приложение запущено")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    await db.disconnect()
    print("Приложение остановлено")


@app.middleware("http")
async def log_request_body(request: Request, call_next):
    # Логируем входящий запрос
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Входящий запрос: {request.method} {request.url} от {client_host}")

    try:
        # Пытаемся прочитать тело запроса для логирования
        body = await request.body()
        if body:
            try:
                body_json = json.loads(body.decode())
                logger.info(f"Тело запроса: {json.dumps(body_json, indent=2)}")
            except json.JSONDecodeError:
                logger.info(f"Тело запроса (не JSON): {body.decode()[:500]}...")  # Ограничиваем длину
    except Exception as e:
        logger.warning(f"Не удалось прочитать тело запроса: {str(e)}")

    # Продолжаем обработку
    response = await call_next(request)

    # Логируем ответ
    logger.info(f"Ответ: {request.method} {request.url} - Status: {response.status_code}")

    return response


# API endpoints для аутентификации
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Регистрация нового пользователя"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = await db.get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        # Создаем пользователя
        user_id = await db.create_user(user.email, user.password)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось создать пользователя"
            )

        # Получаем данные созданного пользователя
        new_user = await db.get_user_by_id(user_id)
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Пользователь создан, но не найден"
            )

        return new_user

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при регистрации"
        )

@app.post("/api/auth/login", response_model=Token)
async def login_user(user: UserLogin):
    """Аутентификация пользователя и получение JWT токена"""
    try:
        # Аутентифицируем пользователя
        authenticated_user = await db.authenticate_user(user.email, user.password)
        if not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль",
                headers={"Authenticate": "Bearer"},
            )

        # Создаем токен
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": authenticated_user["email"]},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"Ошибка при аутентификации: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при аутентификации"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user


@app.post("/api/logs")
async def receive_log(log: Dict[Any, Any] = Body(...)):
    """Принимает лог и сохраняет его в PostgreSQL"""
    try:
        # Извлекаем service из лога или используем значение по умолчанию
        service = log.get('service', 'unknown')

        # Сохраняем в базу данных
        log_id = await db.insert_log(service, log)

        return {
            "status": "success",
            "log_id": log_id,
            "message": "Лог успешно сохранен в БД"
        }
    except Exception as e:
        traceback.print_exception(*sys.exc_info())

        if "Database connection not established" in str(e):
            raise HTTPException(status_code=503, detail="Сервис временно недоступен: нет подключения к БД")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения лога: {str(e)}")


class UpdateLogRequest(BaseModel):
    log_id: int
    analysis: Dict[Any, Any]

@app.put("/api/logs")
async def update_log(request: UpdateLogRequest):
    """Добавляет AI-анализ лога"""

    try:
        # Сохраняем в базу данных
        log_id = await db.update_log(request.log_id, request.analysis)

        return {
            "status": "success",
            "log_id": log_id,
            "message": "Анализ успешно сохранен в БД"
        }
    except Exception as e:
        traceback.print_exception(*sys.exc_info())

        if "Database connection not established" in str(e):
            raise HTTPException(status_code=503, detail="Сервис временно недоступен: нет подключения к БД")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения лога: {str(e)}")


@app.get("/api/logs")
async def get_logs(
        service: Optional[str] = Query(None, description="Фильтр по сервису"),
        hours: Optional[int] = Query(24, description="Количество часов для выборки"),
        limit: Optional[int] = Query(100, description="Лимит записей")
):
    """Получает логи с фильтрацией"""
    try:
        if service:
            # Фильтр по сервису
            logs = await db.get_logs_by_service(service, limit)
        else:
            # Фильтр по времени
            end_time = datetime.now(tz=timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            logs = await db.get_logs_by_time_range(start_time, end_time, limit)

        return {
            "count": len(logs),
            "logs": logs
        }

    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        if "Database connection not established" in str(e):
            raise HTTPException(status_code=503, detail="Сервис временно недоступен: нет подключения к БД")

        raise HTTPException(status_code=500, detail=f"Ошибка получения лога: {str(e)}")


@app.get("/api/health")
async def get_health():
    """Статус сервиса"""
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)