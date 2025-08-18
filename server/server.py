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
async def get_logs():
    """Возвращает все сохранённые логи."""
    return {"logs": logs_storage}
