FROM python:3.11-slim

WORKDIR /app
COPY mcp_hub.py /app/
RUN pip install fastapi uvicorn requests

EXPOSE 4000
CMD ["uvicorn", "mcp_hub:app", "--host", "0.0.0.0", "--port", "4000"]
