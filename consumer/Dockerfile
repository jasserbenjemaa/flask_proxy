FROM python:3.9-slim
ENV PROXY_URL=http://mitm:8091
ENV BACKEND_URL=http://backend:5100
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .

EXPOSE 3000
CMD ["python", "app.py"]
