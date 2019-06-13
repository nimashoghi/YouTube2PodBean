docker build --rm -f "Dockerfile" -t "nimashoghi/youtube2podbean:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean:$TRAVIS_TAG" "nimashoghi/youtube2podbean:latest"
