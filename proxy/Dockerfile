FROM python:3.11-slim


WORKDIR /proxy
COPY . .

RUN apt-get update
RUN pip install mitmproxy httpx

CMD ["mitmdump","-p","8091", "--mode", "reverse:http://backend:5100","-s","intercept.py"]
#CMD ["mitmdump", "-p","8091","-s","intercept.py"]
