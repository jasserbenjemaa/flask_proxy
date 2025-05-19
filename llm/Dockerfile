FROM python:3.12-slim

WORKDIR /llm
COPY . .

RUN apt-get update
RUN  pip install -r requirements.txt

EXPOSE  8008
CMD ["python", "app.py"]