FROM python:3.11-slim


WORKDIR /app
ADD ./ /app

RUN apt-get update
RUN apt-get upgrade -qy

RUN pip install --upgrade pip
RUN pip install mitmproxy httpx

CMD ["mitmdump", "-p","8091","-s","intercept.py"]
#ENTRYPOINT ["mitmweb", "-p", "8091", "--web-port", "8092", "--web-host", "0.0.0.0"]
#ENTRYPOINT ["mitmdump", "-s", "./config.py", "--set", "block_global=false", "--mode", "regular"]
