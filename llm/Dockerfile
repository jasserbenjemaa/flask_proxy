FROM python:3.11-slim
WORKDIR /llm

COPY . .
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["python", "app.py"]
