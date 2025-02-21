FROM python:3.11-slim
WORKDIR /app

COPY . .
RUN pip install -r requirements.txt
RUN pip install -U -q "google-generativeai>=0.8.2"

EXPOSE 5000
CMD ["python", "app.py"]
