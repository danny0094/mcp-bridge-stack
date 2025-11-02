FROM python:3.11-slim
WORKDIR /app
COPY mini_bridge.py .
RUN pip install fastapi uvicorn httpx
CMD ["uvicorn", "mini_bridge:app", "--host", "0.0.0.0", "--port", "4100"]
