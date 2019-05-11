# YouTube2PodBean <!-- omit in toc -->

### A Python application that automatically uploads qualified YouTube videos to PodBean. <!-- omit in toc -->

## Table of Contents <!-- omit in toc -->

- [Setting up the Development Environment](#setting-up-the-development-environment)
- [Running the Image From DockerHub (Recommended)](#running-the-image-from-dockerhub-recommended)
- [Running the Image by Building from Scratch](#running-the-image-by-building-from-scratch)
- [Configuration Environment Variables:](#configuration-environment-variables)

## Setting up the Development Environment

1. Install Python 3 and Poetry.
2. Clone this repository and `cd` into it.
3. Run `poetry install`.

You will need Docker and Docker Compose for building and running the Docker images.

## Running the Image From DockerHub (Recommended)

1. Use the `.env.template` file to create a `.env` file with the proper values.
2. Copy the `docker-compose.yaml` and `.env` files onto your computer/server (e.g. using SCP).
3. Run `docker-compose up -d; docker-compose logs --follow`
4. If you haven't signed in using Podbean yet, then a `podbean_url.txt` file will be generated in your

## Running the Image by Building from Scratch

1. Clone this repository onto your server using `git clone https://github.com/nimashoghi/YouTube2PodBean.git`
2. Use the `.env.template` file to create a `.env` file with the proper values.
3. Run `docker-compose up -d -f docker-compose-build.yaml; docker-compose logs --follow`

## Configuration Environment Variables:

-   `YOUTUTBE_TITLE_PATTERN`: A regex pattern which decides whether a YouTube video will be uploaded to PodBean or not.
-   `YOUTUBE_CHANNEL_ID`: The channel ID of the YouTube channel to watch.
-   `PODBEAN_CLIENT_ID`: The client ID from your PodBean developer application.
-   `PODBEAN_CLIENT_SECRET`: The client secret from your PodBean developer application.
-   `YOUTUBE_API_KEY`: The API key from your YouTube Data V3 developer application.
-   `ACCESS_CODE_PICKLE_PATH`: The file path for the access code pickle file.
-   `PUBLISHED_AFTER_PICKLE_PATH`: The file path for the last check date pickle file.
