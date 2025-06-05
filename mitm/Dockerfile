FROM python:3.12-slim

WORKDIR /mitm
COPY . .

ENV BACKEND_URL=http://backend:5100

RUN apt-get update
RUN pip install -r requirements.txt

EXPOSE 8091
EXPOSE 8092
CMD ["mitmdump","-p","8091", "--mode", "reverse:http://llm:6000","-s","intercept.py"]
#CMD ["mitmdump", "-p","8091","-s","intercept.py"]
