FROM python:3.11-slim

ENV PROXY_PORT=8091
ENV WEB_UI_PORT=8092

WORKDIR /app
ADD ./ /app

RUN apt-get update
RUN apt-get upgrade -qy

RUN pip install --upgrade pip
RUN pip install mitmproxy

RUN useradd --create-home mitmproxyuser
COPY intercept.py /intercept.py

# Copy the mitmproxy configuration script

ENTRYPOINT ["mitmdump", "-p", "8091","-s","./intercept.py"]
#ENTRYPOINT ["mitmweb", "-p", "8091", "--web-port", "8092", "--web-host", "0.0.0.0"]
#ENTRYPOINT ["mitmdump", "-s", "./config.py", "--set", "block_global=false", "--mode", "regular"]
