FROM python:3.11-slim
ENV PROXY_URL=http://mitm:8091
ENV BACKEND_URL=http://backend:5100
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 3000
CMD ["python", "app.py"]
