# Installing Docker-Compose on CoreOS

### Credits to [marszall87's Gist](https://gist.github.com/marszall87/ee7c5ea6f6da9f8968dd)

## Run the following command in your server's terminal:

    mkdir -p /opt/bin \
    && curl -L `curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r '.assets[].browser_download_url | select(contains("Linux") and contains("x86_64"))'` > /opt/bin/docker-compose \
    && chmod +x /opt/bin/docker-compose
