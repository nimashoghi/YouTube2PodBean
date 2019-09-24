FROM python:3-alpine

# copy directory
WORKDIR /app
COPY . .

# install dependencies for pillow
RUN apk add --no-cache jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev

# install build dependencies
RUN apk add --no-cache --virtual .build-deps build-base

# install Python requirements
RUN pip install -r requirements.txt

# remove build dependencies
RUN apk del --purge .build-deps
