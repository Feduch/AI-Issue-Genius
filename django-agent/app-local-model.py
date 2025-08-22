import requests
import json
import time
import logging
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
            n_ctx=4096,
            n_threads=8,
            n_gpu_layers=0,
            temperature=0.1,
            top_p=0.9,
            verbose=False
        )
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.api_url = "https://solar.ninja360.ru/api/logs"

    def fetch_django_logs(self) -> List[Dict]:
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
            error = log_data.get('error')

            prompt = f"""
            [INSTRUCTION]
            Ты — AIssueGenius, эксперт по анализу ошибок Django/Python. 
            Проанализируй эту ошибку и ответь строго по формату ниже.
            [/INSTRUCTION]

            [ERROR_DATA]
            Сообщение об ошибке: {error.get('message')}
            Трасировка кода Traceback: {error.get('stack_trace')}
            [/ERROR_DATA]
            
            [RESPONSE_FORMAT]
            🔍 Проблема: [1 предложение]
            
            🎯 Причина: [1 предложение - техническая причина]
            
            🛠️ Решение:
            - [Конкретное действие]
            
            🛡️ Профилактика: [1 совет]
            [/RESPONSE_FORMAT]
            
            [IMPORTANT]
            - Максимум 1000 слов
            - Без повторений
            - Только по делу
            - В каком файле и в какой строке возникла ошибка
            - Начинай сразу с "🔍 Проблема:"
            [/IMPORTANT]
            
            [SUGGESTION]
            Тут напиши свой ответ и заверши свой ответ закрыв SUGGESTION
            """

            prompt = f"""
            Проанализируй ошибку Django и заполни шаблон:

            ОШИБКА: {error.get('message')}
            СТЕК: {error.get('stack_trace')}

            ЗАПОЛНИ ЭТОТ ШАБЛОН:
            🔍 Проблема: [суть ошибки]
            🎯 Причина: [техническая причина] 
            🛠️ Решение: [конкретные шаги]
            🛡️ Профилактика: [1 совет]

            Файл и строка: [из стека]

            Начинай сразу с "🔍 Проблема:".
            """

            error = log_data.get('error', {})
            stack_trace = error.get('stack_trace', '')

            prompt = f"""
            Проанализируй ошибку Django/Python:

            {stack_trace}

            Напиши краткий анализ этой ошибки. Включи:
            1. В чем проблема
            2. Почему возникла  
            3. Как исправить
            4. Как предотвратить

            Ответ:
            """

            response = self.llm(
                prompt,
                max_tokens=500,
                temperature=0.1,
                stop=["\n\n", "###"],
                stream=False
            )

            result = response["choices"][0]["text"].strip()

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

    def format_analysis_message(self, log_data: Dict, analysis: str) -> str:
        """Форматирование сообщения для Telegram"""
        level = log_data.get('level', 'UNKNOWN')
        service = log_data.get('service', 'UNKNOWN')
        timestamp = log_data.get('timestamp', datetime.now().isoformat())

        message = f"""
            🚨 <b>Новая ошибка обнаружена!</b>
            
            📅 <b>Время:</b> {timestamp} UTC
            🔧 <b>Сервис:</b> {service}
            ⚡ <b>Уровень:</b> {level}
            
            📋 <b>Данные лога:</b>
            <code>{json.dumps(log_data.get('error'), indent=2, ensure_ascii=False)}</code>
            
            🤖 <b>Анализ AIssueGenius:</b>
            {analysis}
            
            #django #error #analysis
        """

        return message.strip()

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
                    message = self.format_analysis_message(log, analysis)

                    # Отправляем в Telegram
                    self.send_telegram_message(message)

                    # Небольшая пауза между сообщениями
                    time.sleep(2)

                logger.info(f"Обработано {len(logs)} ошибок")

            except Exception as e:
                logger.error(f"Критическая ошибка в цикле анализа: {e}")

            # Ожидание следующего цикла
            time.sleep(interval_minutes * 60)


# Конфигурация
CONFIG = {
    'model_path': "../models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf",
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