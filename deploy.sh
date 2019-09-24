#!/bin/sh

docker login -u $DOCKER_USRENAME -p $DOCKER_PASSWORD

docker build --rm -f "services/Dockerfile" -t "$DOCKER_USRENAME/youtube2podbean:$TRAVIS_TAG" .
docker tag "$DOCKER_USRENAME/youtube2podbean:$TRAVIS_TAG" "$DOCKER_USRENAME/youtube2podbean:latest"
docker push $DOCKER_USRENAME/youtube2podbean:$TRAVIS_TAG
docker push $DOCKER_USRENAME/youtube2podbean:latest

docker build --rm -f "services/service.Dockerfile" -t "$DOCKER_USRENAME/youtube2podbean-discord:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG --build-arg YOUTUBE2PODBEAN_SERVICE=app.services.discord ..
docker tag "$DOCKER_USRENAME/youtube2podbean-discord:$TRAVIS_TAG" "$DOCKER_USRENAME/youtube2podbean-discord:latest"
docker push $DOCKER_USRENAME/youtube2podbean-discord:$TRAVIS_TAG
docker push $DOCKER_USRENAME/youtube2podbean-discord:latest

docker build --rm -f "services/podbean.Dockerfile" -t "$DOCKER_USRENAME/youtube2podbean-podbean:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG ..
docker tag "$DOCKER_USRENAME/youtube2podbean-podbean:$TRAVIS_TAG" "$DOCKER_USRENAME/youtube2podbean-podbean:latest"
docker push $DOCKER_USRENAME/youtube2podbean-podbean:$TRAVIS_TAG
docker push $DOCKER_USRENAME/youtube2podbean-podbean:latest

docker build --rm -f "services/service.Dockerfile" -t "$DOCKER_USRENAME/youtube2podbean-wordpress:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG --build-arg YOUTUBE2PODBEAN_SERVICE=app.services.wordpress ..
docker tag "$DOCKER_USRENAME/youtube2podbean-wordpress:$TRAVIS_TAG" "$DOCKER_USRENAME/youtube2podbean-wordpress:latest"
docker push $DOCKER_USRENAME/youtube2podbean-wordpress:$TRAVIS_TAG
docker push $DOCKER_USRENAME/youtube2podbean-wordpress:latest

docker build --rm -f "services/service.Dockerfile" -t "$DOCKER_USRENAME/youtube2podbean-youtube:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG --build-arg YOUTUBE2PODBEAN_SERVICE=app.services.youtube ..
docker tag "$DOCKER_USRENAME/youtube2podbean-youtube:$TRAVIS_TAG" "$DOCKER_USRENAME/youtube2podbean-youtube:latest"
docker push $DOCKER_USRENAME/youtube2podbean-youtube:$TRAVIS_TAG
docker push $DOCKER_USRENAME/youtube2podbean-youtube:latest

docker logout
