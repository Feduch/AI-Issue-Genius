import json
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()


# Модель данных лога (Pydantic)
class ErrorContext(BaseModel):
    db_query: Optional[str] = None
    db_host: Optional[str] = None


class ErrorDetails(BaseModel):
    type: str
    message: str
    stack_trace: str
    context: ErrorContext


class LogModel(BaseModel):
    timestamp: str
    level: str
    service: str
    request_id: str
    error: ErrorDetails


# Хранилище логов (вместо БД для примера)
logs_storage = []


@app.post("/api/logs")
async def receive_log(log: LogModel):
    """Принимает лог и сохраняет его."""
    logs_storage.append(log.dict())

    # Здесь можно добавить вызов AI-агента для анализа
    print(f"Получен лог: {log}")

    return {"status": "success", "log_id": len(logs_storage) - 1}


@app.get("/api/logs")
async def get_logs(
        service: Optional[str] = Query(None, description="Фильтр по сервису (например: django, nginx, postgresql)")
):
    """Возвращает логи с возможностью фильтрации и удаления."""

    filtered_logs = logs_storage.copy()

    # Фильтрация по service
    if service:
        filtered_logs = [log for log in filtered_logs if log.get('service') == service]

    # Удаляем логи после получения, если указано delete_after=true
    logs_to_return = filtered_logs.copy()

    if service:
        # Удаляем логи из хранилища
        global logs_storage
        logs_storage = [log for log in logs_storage if log.get('service') != service]
        print(f"Удалено логов сервиса '{service}': {len(filtered_logs)}")

    return logs_to_return
