FROM python:3.11-slim


WORKDIR /proxy
COPY . .

RUN apt-get update
RUN pip install mitmproxy httpx jsonschema


CMD ["mitmdump", "-p","8091","-s","intercept.py"]
