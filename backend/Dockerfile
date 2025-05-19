FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 5100
CMD ["python", "app.py"]
