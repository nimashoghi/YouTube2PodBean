docker login -u $DOCKER_USRENAME -p $DOCKER_PASSWORD

docker build --rm -f "Dockerfile" -t "nimashoghi/youtube2podbean:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean:$TRAVIS_TAG" "nimashoghi/youtube2podbean:latest"
docker push youtube2podbean:$TRAVIS_TAG
docker push youtube2podbean:latest

docker build --rm -f "services/discord.Dockerfile" -t "nimashoghi/youtube2podbean-discord:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean-discord:$TRAVIS_TAG" "nimashoghi/youtube2podbean-discord:latest"
docker push youtube2podbean-discord:$TRAVIS_TAG
docker push youtube2podbean-discord:latest

docker build --rm -f "services/podbean.Dockerfile" -t "nimashoghi/youtube2podbean-podbean:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean-podbean:$TRAVIS_TAG" "nimashoghi/youtube2podbean-podbean:latest"
docker push youtube2podbean-podbean:$TRAVIS_TAG
docker push youtube2podbean-podbean:latest

docker build --rm -f "services/wordpress.Dockerfile" -t "nimashoghi/youtube2podbean-wordpress:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean-wordpress:$TRAVIS_TAG" "nimashoghi/youtube2podbean-wordpress:latest"
docker push youtube2podbean-wordpress:$TRAVIS_TAG
docker push youtube2podbean-wordpress:latest

docker build --rm -f "services/youtube.Dockerfile" -t "nimashoghi/youtube2podbean-youtube:$TRAVIS_TAG" .
docker tag "nimashoghi/youtube2podbean-youtube:$TRAVIS_TAG" "nimashoghi/youtube2podbean-youtube:latest"
docker push youtube2podbean-youtube:$TRAVIS_TAG
docker push youtube2podbean-youtube:latest
