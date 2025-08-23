import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создает пул подключений к БД"""
        database_url = os.getenv(
            "DATABASE_URL"
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

    async def insert_log(self, service: str, log_data: Dict[Any, Any]) -> int:
        """Вставляет лог в базу данных и возвращает ID"""
        if not self.pool:
            raise Exception("Database connection not established")

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

    async def update_log(self, log_id: int, analysis: Dict[Any, Any]) -> int:
        """Вставляет лог в базу данных и возвращает ID"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                UPDATE logs 
                SET ai_analysis = $1, 
                    analysis_time = NOW()
                WHERE id = $2
                RETURNING id
            """

            updated_id = await conn.fetchval(
                query,
                analysis,
                log_id
            )
            return updated_id

    async def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Получает лог по ID"""
        if not self.pool:
            raise Exception("Database connection not established")

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
        if not self.pool:
            raise Exception("Database connection not established")

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
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                SELECT id, timestamp, service, log, ai_analysis, analysis_time
                FROM logs 
                WHERE service = $1 AND analysis_time is null
                ORDER BY id ASC
                LIMIT $2
            """

            rows = await conn.fetch(query, service, limit)
            return [dict(row) for row in rows]

    async def get_total_logs_count(self) -> int:
        """Возвращает общее количество логов"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM logs")


# Глобальный экземпляр базы данных
db = Database()