FROM nimashoghi/python AS exporter

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN poetry export -f requirements.txt

FROM python:3-stretch

WORKDIR /app
COPY . .
COPY --from=exporter /app/requirements.txt ./

RUN pip install -r requirements.txt

CMD ["python", "-m", "$YOUTUBE2PODBEAN_SERVICE"]
