import os
import requests
from dotenv import load_dotenv
from llama_cpp import Llama

load_dotenv()

HF_TOKEN = os.getenv('HF_TOKEN')

# Создаем папку для моделей
os.makedirs("./models", exist_ok=True)

model_url = f"https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf?token={HF_TOKEN}"
model_path = "./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"

# Скачиваем модель если нет
if not os.path.exists(model_path):
    print("Downloading model...")
    response = requests.get(model_url, timeout=10)
    with open(model_path, 'wb') as f:
        f.write(response.content)
    print("Model downloaded!")

# Загружаем модель
llm = Llama(
    model_path=model_path,
    n_ctx=4096,
    n_gpu_layers=35,  # Для GPU
    verbose=False
)

# Теперь можно использовать
response = llm("Анализ ошибки Python:", max_tokens=200)
print(response['choices'][0]['text'])