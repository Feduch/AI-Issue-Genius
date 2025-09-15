import os
import json
import asyncpg
import bcrypt
from typing import Optional, Dict, Any, List
from datetime import datetime


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создает пул подключений к БД"""
        database_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/ai_issue_genius"

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

        # Методы для работы с пользователями

    async def create_user(self, email: str, password: str) -> Optional[int]:
        """Создает нового пользователя с хешированным паролем"""
        if not self.pool:
            raise Exception("Database connection not established")

        # Хешируем пароль
        hashed_password = self._hash_password(password)

        async with self.pool.acquire() as conn:
            try:
                query = """
                       INSERT INTO users (email, password_hash, created_at)
                       VALUES ($1, $2, NOW())
                       RETURNING id
                   """

                user_id = await conn.fetchval(query, email, hashed_password)
                return user_id
            except asyncpg.exceptions.UniqueViolationError:
                return None  # Пользователь уже существует

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентифицирует пользователя по email и паролю"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                   SELECT id, email, password_hash, created_at, is_active
                   FROM users 
                   WHERE email = $1 AND is_active = true
               """

            row = await conn.fetchrow(query, email)
            if not row:
                return None

            user_data = dict(row)

            # Проверяем пароль
            if self._verify_password(password, user_data['password_hash']):
                # Не возвращаем хеш пароля в результатах
                user_data.pop('password_hash', None)
                return user_data

            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                   SELECT id, email, created_at, is_active
                   FROM users 
                   WHERE id = $1
               """

            row = await conn.fetchrow(query, user_id)
            if row:
                return dict(row)
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по email"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                   SELECT id, email, created_at, is_active
                   FROM users 
                   WHERE email = $1
               """

            row = await conn.fetchrow(query, email)
            if row:
                return dict(row)
            return None

    async def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Обновляет пароль пользователя"""
        if not self.pool:
            raise Exception("Database connection not established")

        hashed_password = self._hash_password(new_password)

        async with self.pool.acquire() as conn:
            query = """
                   UPDATE users 
                   SET password_hash = $1
                   WHERE id = $2
               """

            result = await conn.execute(query, hashed_password, user_id)
            return "UPDATE 1" in result

    async def deactivate_user(self, user_id: int) -> bool:
        """Деактивирует пользователя"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                   UPDATE users 
                   SET is_active = false
                   WHERE id = $1
               """

            result = await conn.execute(query, user_id)
            return "UPDATE 1" in result

    async def get_all_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        if not self.pool:
            raise Exception("Database connection not established")

        async with self.pool.acquire() as conn:
            query = """
                   SELECT id, email, created_at, is_active
                   FROM users 
                   ORDER BY created_at DESC
                   LIMIT $1
               """

            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]

        # Вспомогательные методы для работы с паролями

    def _hash_password(self, password: str) -> str:
        """Хеширует пароль с использованием bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль против хеша"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False

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
                json.dumps(analysis),
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