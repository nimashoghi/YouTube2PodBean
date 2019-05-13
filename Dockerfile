FROM python:3-stretch

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "-m", "app.main"]
