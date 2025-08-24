import hashlib
from functools import lru_cache
from typing import Dict


class LogAnalyzer:
    def __init__(self):
        self.processed_errors = set()
        self.error_cache = {}  # Кэш для результатов анализа

    def _get_error_hash(self, log_data: Dict) -> str:
        """Создает уникальный хеш для ошибки на основе ключевых параметров"""
        error = log_data.get('error', {})
        # Ключевые поля для определения уникальности ошибки
        hash_string = f"{error.get('type')}-{error.get('message')}-{log_data.get('service')}"
        return hashlib.md5(hash_string.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def analyze_error_cached(self, error_hash: str, log_data: Dict) -> str:
        """Анализирует ошибку с использованием кэша"""
        # Если ошибка уже анализировалась, возвращаем закэшированный результат
        if error_hash in self.error_cache:
            return self.error_cache[error_hash]

        # Новый анализ
        analysis = self.analyze_log(log_data)
        self.error_cache[error_hash] = analysis
        return analysis

    def process_logs(self):
        """Основной метод обработки с кэшированием"""
        logs = self.get_django_logs(hours=1)

        for log in logs:
            error_hash = self._get_error_hash(log)

            # Пропускаем уже обработанные ошибки
            if error_hash in self.processed_errors:
                continue

            # Анализируем с использованием кэша
            analysis = self.analyze_error_cached(error_hash, log)

            # Отправляем в Telegram только если это новая ошибка
            if error_hash not in self.processed_errors:
                self.send_to_telegram(log, analysis)
                self.processed_errors.add(error_hash)