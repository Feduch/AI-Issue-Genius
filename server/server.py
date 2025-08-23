import sys
import uvicorn
import traceback
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Query, Body, HTTPException
from typing import Optional, Dict, Any, AsyncIterator

from jinja2.ext import debug

from database import db

app = FastAPI(title="AI Issue Genius API", version="1.0.0")

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


@app.put("/api/logs")
async def update_log(log_id: int, analysis: Dict[Any, Any] = Body(...)):
    """Добавляет AI-анализ лога"""

    try:
        # Сохраняем в базу данных
        log_id = await db.update_log(log_id, analysis)

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