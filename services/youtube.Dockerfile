ARG BASE_VERSION=latest
FROM nimashoghi/youtube2podbean:${BASE_VERSION}

CMD ["python", "-m", "app.services.youtube"]
