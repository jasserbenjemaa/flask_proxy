FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN  pip install pyproject.toml

EXPOSE 5100
CMD ["python", "main.py"]