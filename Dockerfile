FROM ubuntu:14.10
# need this image, so that pyc works
RUN apt-get update
RUN apt-get -y install python3-tk
ADD . /code/
