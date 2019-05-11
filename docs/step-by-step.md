# Step by Step Setup Guide

### [Make sure you have docker-compose installed](./coreos-docker-compose.md)

## Step 1: Add `docker-compose.yaml`

    cat >> docker-compose.yaml <<EOL
    version: "3.1"
    services:
        watcher:
            image: "nimashoghi/youtube2podbean:latest"
            env_file:
                - ./.env
            volumes:
                - ./pickles:/app/pickles
            ports:
                - "23808:23808"
            restart: always
            stdin_open: true
            tty: true
    EOL

---

## Step 2: Add `.env`

    cat >> .env <<EOL
    YOUTUTBE_TITLE_PATTERN=.+

    YOUTUBE_CHANNEL_ID={channel id here}

    PODBEAN_CLIENT_ID={client id}
    PODBEAN_CLIENT_SECRET={client secret}
    YOUTUBE_API_KEY={api key}

    ACCESS_CODE_PICKLE_PATH=/app/pickles/access_code.pickle
    PUBLISHED_AFTER_PICKLE_PATH=/app/pickles/published_after.pickle
    EOL

---

## Step 3: Run the Program

    docker-compose up -d; docker-compose logs --follow
