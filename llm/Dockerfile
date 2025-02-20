FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install -U -q "google-generativeai>=0.8.2"
COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
