ARG BASE_VERSION=latest
FROM nimashoghi/youtube2podbean:${BASE_VERSION}

# install ffmpeg
RUN apk add --no-cache ffmpeg

CMD ["python", "-m", "app.services.podbean"]
