from llama_cpp import Llama

# Инициализация модели
llm = Llama(
    model_path="./models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf",  # Путь к модели
    n_ctx=2048,           # Максимальный контекст (зависит от RAM)
    n_threads=8,          # Число CPU-потоков
    n_gpu_layers=0,       # 0 = только CPU, >0 — часть слоёв на GPU (если есть)
    verbose=True          # Логирование
)

# Промпт для анализа лога
log_json = """
{
  "level": "ERROR",
  "service": "django",
  "error": {
    "type": "DatabaseError",
    "message": "Connection to PostgreSQL failed: timeout"
  }
}
"""

prompt = f"""
Ты — AIssueGenius, эксперт по анализу ошибок. Проанализируй лог и предложи решение.
Лог:
```json
{log_json}
```
"""

response = llm(
    prompt,
    max_tokens=512,
    stream=False
)

print(response)

print(response["choices"][0]["text"])