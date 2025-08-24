import sys
import json
import uvicorn
import logging
import traceback
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Query, Body, HTTPException, Request
from typing import Optional, Dict, Any

from jinja2.ext import debug

from database import db

app = FastAPI(title="AI Issue Genius API", version="1.0.0")

logger = logging.getLogger(__name__)

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
    print(f"Входящий запрос: {request.method} {request.url} от {client_host}")

    try:
        # Пытаемся прочитать тело запроса для логирования
        body = await request.body()
        if body:
            try:
                body_json = json.loads(body.decode())
                logger.info(f"Тело запроса: {json.dumps(body_json, indent=2)}")
                print(f"Тело запроса: {json.dumps(body_json, indent=2)}")
            except json.JSONDecodeError:
                logger.info(f"Тело запроса (не JSON): {body.decode()[:500]}...")  # Ограничиваем длину
                print(f"Тело запроса (не JSON): {body.decode()[:500]}...")
    except Exception as e:
        logger.warning(f"Не удалось прочитать тело запроса: {str(e)}")

    # Продолжаем обработку
    response = await call_next(request)

    # Логируем ответ
    logger.info(f"Ответ: {request.method} {request.url} - Status: {response.status_code}")

    return response


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