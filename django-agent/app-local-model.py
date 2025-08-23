import requests
import json
import time
import logging
from utils.django import prepare_ai_request
from datetime import datetime, timedelta
from typing import List, Dict, Any
from llama_cpp import Llama

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LogAnalyzerService:
    def __init__(self, model_path: str, telegram_bot_token: str, telegram_chat_id: str):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=16384,
            n_threads=12,
            n_gpu_layers=0,
            temperature=0.1,
            top_p=0.9,
            verbose=False
        )

        logger.info("Информация о модели:")
        logger.info(f"Имя модели: {self.llm.model_path}")
        logger.info(f"Размер контекста: {self.llm.n_ctx}")
        # logger.info(f"Количество параметров: {self.llm.n_params()}")
        logger.info(f"Размер словаря: {self.llm.n_vocab()}")

        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.api_url = "https://solar.ninja360.ru/api/logs"

    def fetch_logs(self) -> List[Dict]:
        """Получение логов Django за указанный период"""
        try:
            params = {
                'service': 'django'
            }

            logger.info(f"Запрос логов с параметрами: {params}")

            response = requests.get(
                self.api_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            logs = response.json()
            logger.info(f"Получено {len(logs)} логов Django")
            return logs

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении логов: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return []

    def analyze_log(self, log_data: Dict) -> str:
        """Анализ лога с помощью AI модели"""
        try:
            # Подготавливаем структурированный запрос
            ai_request = prepare_ai_request(log_data)

            # Создаем промпт для модели
            prompt = self.create_analysis_prompt(ai_request)

            logger.info(f"prompt {prompt}")

            # Формируем сообщения для chat-style модели
            messages = [
                {"role": "system",
                 "content": "Ты опытный Python/Django разработчик, специализирующийся на анализе ошибок и поиске решений."},
                {"role": "user", "content": prompt}
            ]

            # Выполняем запрос к модели
            response = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=1024,
                frequency_penalty=0.5,
                temperature=0.3,  # Низкая температура для детерминированных ответов
                stop=["</analysis>", "###", "---", "\n\n"]
            )

            result = response['choices'][0]['message']['content']

            logger.info(f"result {result}")

            return result

        except Exception as e:
            logger.error(f"Ошибка при анализе лога: {e}")
            return f"Ошибка анализа: {str(e)}"

    def send_telegram_message(self, message: str) -> bool:
        """Отправка сообщения в Telegram с разбивкой на части"""
        try:
            # Разбиваем сообщение на части по 4000 символов
            max_length = 4000
            messages = [message[i:i + max_length] for i in range(0, len(message), max_length)]

            for i, msg_part in enumerate(messages):
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
                payload = {
                    'chat_id': self.telegram_chat_id,
                    'text': f"Часть {i + 1}/{len(messages)}\n\n{msg_part}",
                    'parse_mode': 'HTML'
                }

                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                time.sleep(1)  # Пауза между сообщениями

            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False

    def create_analysis_prompt(self, ai_request):
        """
        Создает текстовый промпт из структурированного запроса
        """
        prompt = f"""
                    Ты — AIssueGenius, эксперт по созданию технических issue.             
                    На основе анализа ошибки создай структурированное issue для разработчиков.

                    ДАННЫЕ ДЛЯ АНАЛИЗА:

                    КОНТЕКСТ ОШИБКИ:
                    - Время: {ai_request['error_context']['timestamp']}
                    - Окружение: {ai_request['error_context']['environment']}
                    - Приложение: {ai_request['error_context']['application']}
                    - Сервис: {ai_request['error_context']['service']}
                    - Метод: {ai_request['error_context']['request_method']}
                    - Путь: {ai_request['error_context']['request_path']}

                    ДЕТАЛИ ОШИБКИ:
                    Тип: {ai_request['error_details']['type']}
                    Сообщение: {ai_request['error_details']['message']}

                    TRACEBACK:
                    {chr(10).join(ai_request['error_details']['traceback'][-5:])}

                    КОД С ОШИБКОЙ:
                    Файл: {ai_request['error_details']['code_context'].get('file', 'unknown')}
                    Строка: {ai_request['error_details']['code_context'].get('line', 'unknown')}
                    Код: {ai_request['error_details']['code_context'].get('code_snippet', 'unknown')}

                    ОКРУЖЕНИЕ:
                    Python: {ai_request['environment_info']['python_version']}
                    Django: {ai_request['environment_info']['django_version']}
                    Debug: {ai_request['environment_info']['debug_mode']}
                    Database: {ai_request['environment_info']['database_engine']}

                    ИНСТРУКЦИЯ ДЛЯ СОЗДАНИЯ ISSUE:
                    1. Title: Краткое описательное название (максимум 10 слов)                
                    2. Description:                
                        - Краткое описание проблемы                
                        - Шаги для воспроизведения (если применимо)                
                    3. Labels: Добавь соответствующие метки (через запятую)                
                    4. Priority: Определи приоритет (Critical, High, Medium, Low)                
                    5. Assignee: Укажи suggested assignee (backend, frontend, devops, database)                
                    6. Milestone: Предложи milestone если это критичный баг                
                    7 .Checklist: Создай чеклист для решения проблемы

                    ФОРМАТ ВЫВОДА:
                    Выведи результат строго в формате JSON:
                    {{
                      "title": "string",
                      "description": "string",
                      "labels": "string,string,string",
                      "priority": "Critical|High|Medium|Low",
                      "assignee": "backend|frontend|devops|database",
                      "milestone": "string|null",
                      "checklist": [
                        "Шаг 1: Описание действия",
                        "Шаг 2: Описание действия"
                      ]
                    }}

                    ПРИМЕР ХОРОШЕГО ISSUE:
                    Title: "Тайм-аут соединения с базой данных в приложении Django"
                    Priority: "High"
                    Labels: "bug,database,backend"
                    Assignee: "backend"

                    Будь конкретным и практичным в рекомендациях!
                """

        return prompt


    def run_analysis_cycle(self, interval_minutes: int = 30):
        """Основной цикл анализа"""
        logger.info("Запуск сервиса анализа логов...")

        while True:
            try:
                # Получаем логи
                logs = self.fetch_django_logs()  # За последний час

                if not logs:
                    logger.info("Новых ошибок не обнаружено")
                    time.sleep(interval_minutes * 60)
                    continue

                # Анализируем каждую ошибку
                for log in logs:
                    analysis = self.analyze_log(log)

                    # Отправляем в Telegram
                    self.send_telegram_message(analysis)

                    # Небольшая пауза между сообщениями
                    time.sleep(2)

                logger.info(f"Обработано {len(logs)} ошибок")

            except Exception as e:
                logger.error(f"Критическая ошибка в цикле анализа: {e}")

            # Ожидание следующего цикла
            time.sleep(interval_minutes * 60)


# Конфигурация
CONFIG = {
    'model_path': "../models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
    'telegram_bot_token': "6630832399:AAHs_e3g9C0Uf03DRJCuie2P0bQY_YaVQis",  # Замените на реальный токен
    'telegram_chat_id': 94486111,  # Замените на реальный ID чата
    'check_interval_minutes': 30
}

if __name__ == "__main__":
    service = LogAnalyzerService(
        model_path=CONFIG['model_path'],
        telegram_bot_token=CONFIG['telegram_bot_token'],
        telegram_chat_id=CONFIG['telegram_chat_id']
    )

    service.run_analysis_cycle(interval_minutes=CONFIG['check_interval_minutes'])