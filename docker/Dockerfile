FROM ubuntu:18.04

RUN apt update && apt -y install git python3.6 python3.6-dev python3-pip && apt clean
RUN python3.6 -m pip install pytest pytest-cov

