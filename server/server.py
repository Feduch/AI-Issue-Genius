from fastapi import FastAPI, Query, Body
from typing import Optional, Dict, Any

app = FastAPI()

# Хранилище логов (вместо БД для примера)
logs_storage = []


@app.post("/api/logs")
async def receive_log(log: Dict[Any, Any] = Body(...)):
    """Принимает лог и сохраняет его."""
    # Здесь можно добавить вызов AI-агента для анализа
    print(f"Получен лог: {log}")

    logs_storage.append(log)
    return {"status": "success", "log_id": len(logs_storage) - 1}


@app.get("/api/logs")
async def get_logs(
        service: Optional[str] = Query(None, description="Фильтр по сервису (например: django, nginx, postgresql)")
):
    """Возвращает логи с возможностью фильтрации и удаления."""
    global logs_storage

    logs_to_return = [item for item in logs_storage]

    # Фильтрация по service
    if service:
        logs_to_return = [item for item in logs_storage if item.get('service') == service]

        # Удаляем их из исходного массива
        logs_storage = [item for item in logs_storage if item.get('service') != service]

    return logs_to_return
