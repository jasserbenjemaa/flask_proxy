FROM python:3.12-slim
WORKDIR /app

ENV SUPABASE_URL=https://kxohmzstgbgefpdzvreg.supabase.co
ENV SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4b2htenN0Z2JnZWZwZHp2cmVnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzY2NzIxNSwiZXhwIjoyMDYzMjQzMjE1fQ.JY-woXRALTJF9TmIPV3b__Fn6sVrjWrUB5A4bNfpsZc

COPY . .
RUN pip install -r requirements.txt

EXPOSE 5100
CMD ["python", "app.py"]
