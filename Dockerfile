FROM nimashoghi/python AS exporter

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN poetry export -f requirements.txt

FROM python:3-alpine

# copy directory
WORKDIR /app
COPY . .

# install ffmpeg
RUN apk add --no-cache ffmpeg

# install Python requirements
COPY --from=exporter /app/requirements.txt ./
RUN pip install -r requirements.txt

ARG YOUTUBE2PODBEAN_SERVICE
CMD ["python", "-m", "${YOUTUBE2PODBEAN_SERVICE}"]
