FROM python:3.11-slim


WORKDIR /proxy
COPY intercept.py .

RUN apt-get update
RUN pip install mitmproxy httpx

CMD ["mitmdump", "-p","8091","-s","intercept.py"]
