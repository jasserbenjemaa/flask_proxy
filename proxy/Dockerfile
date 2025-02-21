FROM python:3.11-slim


WORKDIR /proxy
COPY intercept.py .

RUN apt-get update
RUN pip install mitmproxy httpx

CMD ["mitmdump", "-p","8091","-s","intercept.py"]
#ENTRYPOINT ["mitmweb", "-p", "8091", "--web-port", "8092", "--web-host", "0.0.0.0"]
#ENTRYPOINT ["mitmdump", "-s", "./config.py", "--set", "block_global=false", "--mode", "regular"]
