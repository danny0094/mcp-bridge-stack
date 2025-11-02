FROM python:3.11-slim

WORKDIR /app

COPY mini_prompt_injector.py .

RUN pip install fastapi uvicorn requests

EXPOSE 11434

CMD ["uvicorn", "mini_prompt_injector:app", "--host", "0.0.0.0", "--port", "11434"]
