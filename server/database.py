import asyncpg
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создает пул подключений к БД"""
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://ai_issue_genius:ai_issue_genius@ai-issue-genius-db/ai_issue_genius"
        )

        self.pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        print("Подключение к БД установлено")

    async def disconnect(self):
        """Закрывает пул подключений"""
        if self.pool:
            await self.pool.close()
            print("Подключение к БД закрыто")

    async def init_db(self):
        """Инициализирует таблицу если она не существует"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id BIGSERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    service VARCHAR(100) NOT NULL,
                    log JSONB,
                    ai_analysis JSONB,
                    analysis_time TIMESTAMP WITH TIME ZONE
                )
            ''')
            print("Таблица logs готова к работе")

    async def insert_log(self, service: str, log_data: Dict[Any, Any]) -> int:
        """Вставляет лог в базу данных и возвращает ID"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO logs (service, log)
                VALUES ($1, $2)
                RETURNING id
            """

            log_id = await conn.fetchval(
                query,
                service,
                json.dumps(log_data)
            )
            return log_id

    async def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Получает лог по ID"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, timestamp, service, log, ai_analysis, analysis_time
                FROM logs WHERE id = $1
            """

            row = await conn.fetchrow(query, log_id)
            if row:
                return dict(row)
            return None

    async def get_logs_by_time_range(self, start_time: datetime, end_time: datetime,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Получает логи за временной промежуток"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, timestamp, service, log, ai_analysis, analysis_time
                FROM logs 
                WHERE timestamp BETWEEN $1 AND $2
                ORDER BY timestamp DESC
                LIMIT $3
            """

            rows = await conn.fetch(query, start_time, end_time, limit)
            return [dict(row) for row in rows]

    async def get_logs_by_service(self, service: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получает логи по сервису"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, timestamp, service, log, ai_analysis, analysis_time
                FROM logs 
                WHERE service = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """

            rows = await conn.fetch(query, service, limit)
            return [dict(row) for row in rows]

    async def get_total_logs_count(self) -> int:
        """Возвращает общее количество логов"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM logs")


# Глобальный экземпляр базы данных
db = Database()