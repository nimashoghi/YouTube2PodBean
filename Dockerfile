FROM python:3-stretch

# install ffmpeg
RUN apt-get update \
    && apt-get --yes install ffmpeg

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "-m", "app.main"]
