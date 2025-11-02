FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn

COPY . .

EXPOSE 4210

CMD ["uvicorn", "mcp_time:app", "--host", "0.0.0.0", "--port", "4210"]
