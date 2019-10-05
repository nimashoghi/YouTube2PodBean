#!/bin/sh

docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD

docker build --rm -f "services/Dockerfile" -t "$DOCKER_USERNAME/youtube2podbean:$TRAVIS_TAG" .
docker tag "$DOCKER_USERNAME/youtube2podbean:$TRAVIS_TAG" "$DOCKER_USERNAME/youtube2podbean:latest"
docker push $DOCKER_USERNAME/youtube2podbean:$TRAVIS_TAG
docker push $DOCKER_USERNAME/youtube2podbean:latest

docker build --rm -f "services/discord.Dockerfile" -t "$DOCKER_USERNAME/youtube2podbean-discord:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG ..
docker tag "$DOCKER_USERNAME/youtube2podbean-discord:$TRAVIS_TAG" "$DOCKER_USERNAME/youtube2podbean-discord:latest"
docker push $DOCKER_USERNAME/youtube2podbean-discord:$TRAVIS_TAG
docker push $DOCKER_USERNAME/youtube2podbean-discord:latest

docker build --rm -f "services/podbean.Dockerfile" -t "$DOCKER_USERNAME/youtube2podbean-podbean:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG ..
docker tag "$DOCKER_USERNAME/youtube2podbean-podbean:$TRAVIS_TAG" "$DOCKER_USERNAME/youtube2podbean-podbean:latest"
docker push $DOCKER_USERNAME/youtube2podbean-podbean:$TRAVIS_TAG
docker push $DOCKER_USERNAME/youtube2podbean-podbean:latest

docker build --rm -f "services/wordpress.Dockerfile" -t "$DOCKER_USERNAME/youtube2podbean-wordpress:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG ..
docker tag "$DOCKER_USERNAME/youtube2podbean-wordpress:$TRAVIS_TAG" "$DOCKER_USERNAME/youtube2podbean-wordpress:latest"
docker push $DOCKER_USERNAME/youtube2podbean-wordpress:$TRAVIS_TAG
docker push $DOCKER_USERNAME/youtube2podbean-wordpress:latest

docker build --rm -f "services/youtube.Dockerfile" -t "$DOCKER_USERNAME/youtube2podbean-youtube:$TRAVIS_TAG" --build-arg BASE_VERSION=$TRAVIS_TAG ..
docker tag "$DOCKER_USERNAME/youtube2podbean-youtube:$TRAVIS_TAG" "$DOCKER_USERNAME/youtube2podbean-youtube:latest"
docker push $DOCKER_USERNAME/youtube2podbean-youtube:$TRAVIS_TAG
docker push $DOCKER_USERNAME/youtube2podbean-youtube:latest

docker logout
