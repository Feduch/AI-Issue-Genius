import os
import re
import requests
import json
import time
import logging
from dotenv import load_dotenv
from utils.django import prepare_ai_request
from typing import List, Dict, Any

load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GITLAB_TOKEN = os.getenv('GITLAB_TOKEN')

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LogAnalyzerService:
    def __init__(self, telegram_bot_token: str, telegram_chat_id: str):
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

            count = response.json().get('count')
            logs = response.json().get('logs')

            logger.info(f"Получено {count} логов Django")
            return logs

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении логов: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return []

    def analyze_log(self, log_data: Dict) -> str:
        """
        Анализирует ошибку Python/Django с помощью DeepSeek API
        """
        try:
            # Подготавливаем структурированный запрос
            ai_request = prepare_ai_request(log_data)

            # Создаем промпт для модели
            prompt = self.create_analysis_prompt(ai_request)

            # logger.info(f"prompt {prompt}")

            url = "https://api.deepseek.com/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "deepseek-coder",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты опытный Python/Django разработчик, специализирующийся на анализе ошибок и поиске решений."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }

            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()
                return result['choices'][0]['message']['content']

            except Exception as e:
                return f"Ошибка при обращении к API: {str(e)}"
        except Exception as e:
            logger.error(f"Ошибка при анализе лога: {e}")
            return f"Ошибка анализа: {str(e)}"

    def send_telegram_message(self, message: str, issue_url: str) -> bool:
        """Отправка сообщения в Telegram с разбивкой на части"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': f"{message}\n\n[Ссылка на issue]({issue_url})",
                'parse_mode': 'Markdown'
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

    def prepare_analysis(self, payload: str) -> Dict[str, Any]:
        """
        Получает json из анализа
        :param payload:
        :return:
        """
        pattern = r'```json\s*(.*?)\s*```'
        match = re.search(pattern, payload, re.DOTALL)
        if match:
            json_string = match.group(1).strip()
            payload = json.loads(json_string)

        return payload


    def create_issue(self, payload: Dict[str, Any]) -> str:
        """
        Создает issue на основе ответа ИИ агента
        :param payload:
        :return: url to issue
        """
        checklist = '## Чек-лист\n\n'

        for item in payload.get('checklist', []):
            checklist += f"- [ ] {item}\n"


        url = "https://gitlab.com/api/v4/projects/10046060/issues"
        headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
        data = {
            "title": payload.get('title'),
            "description": f"{payload.get('description')}\n\n{checklist}",
            "labels": f"{payload.get('labels')},priority::{payload.get('priority').lower()}",
        }

        response = requests.post(url, headers=headers, json=data)
        return response.json().get('web_url')


    def save_analysis(self, log_id: int, analysis: Dict[str, Any]):
        """
        Сохраняет ответ от ИИ в базу
        :param analysis:
        :return:
        """
        logger.info(f"log_id ------------- {log_id} ------------------------")
        logger.info(analysis)
        logger.info(f"=======================================================")

        try:
            logger.info(f"Сохраняет анализ лога log_id {log_id}")

            headers = {
                'Content-Type': 'application/json'
            }

            response = requests.put(
                self.api_url,
                json={
                    'log_id': log_id,
                    'analysis': analysis
                },
                timeout=30,
                headers=headers
            )
            response.raise_for_status()

            logs = response.json()
            logger.info(f"Анализ лога успешно сохранен log_id {log_id} logs {logs}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении логов: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")


    def run_analysis_cycle(self, interval_minutes: int = 30):
        """Основной цикл анализа"""
        logger.info("Запуск сервиса анализа логов...")

        while True:
            try:
                # Получаем логи
                logs = self.fetch_logs()  # За последний час

                if not logs:
                    logger.info("Новых ошибок не обнаружено")
                    time.sleep(interval_minutes * 60)
                    continue

                # Анализируем каждую ошибку
                for log in logs:
                    log_id = log.get('id')
                    log_data = json.loads(log.get('log'))

                    analysis = self.analyze_log(log_data)

                    payload = self.prepare_analysis(analysis)

                    # Сохранить ответ от ИИ
                    self.save_analysis(log_id, payload)

                    # Создает issue
                    issue_url = self.create_issue(payload)

                    # Отправляем в Telegram
                    self.send_telegram_message(analysis, issue_url)

                    # Небольшая пауза между сообщениями
                    time.sleep(2)

                logger.info(f"Обработано {len(logs)} ошибок")

            except Exception as e:
                logger.error(f"Критическая ошибка в цикле анализа: {e}")

            # Ожидание следующего цикла
            time.sleep(interval_minutes * 60)


# Конфигурация
CONFIG = {
    'telegram_bot_token': TELEGRAM_TOKEN,  # Замените на реальный токен
    'telegram_chat_id': 94486111,  # Замените на реальный ID чата
    'check_interval_minutes': 30
}

if __name__ == "__main__":
    service = LogAnalyzerService(
        telegram_bot_token=CONFIG['telegram_bot_token'],
        telegram_chat_id=CONFIG['telegram_chat_id']
    )

    service.run_analysis_cycle(interval_minutes=CONFIG['check_interval_minutes'])