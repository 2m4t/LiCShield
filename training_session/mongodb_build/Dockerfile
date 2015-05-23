FROM python:2.7.9-wheezy

ENV DEBIAN_FRONTEND noninteractive

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r mongodb && useradd -r -g mongodb mongodb

RUN apt-get update \
        && apt-get install -y curl numactl \
        && rm -rf /var/lib/apt/lists/*

# grab gosu for easy step-down from root
#RUN gpg --keyserver hkp://pool.sks-keyservers.net:80 --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4

COPY mongodb1.gpg /
COPY mongodb2.gpg /
RUN gpg --import /mongodb1.gpg && gpg --import /mongodb2.gpg && rm /mongodb1.gpg /mongodb2.gpg

RUN curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture)" \
        && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture).asc" \
        && gpg --verify /usr/local/bin/gosu.asc \
        && rm /usr/local/bin/gosu.asc \
        && chmod +x /usr/local/bin/gosu

#ENV MONGO_RELEASE_FINGERPRINT DFFA3DCF326E302C4787673A01C4E7FAAAB2461C
#RUN gpg --keyserver hkp://pool.sks-keyservers.net:80 --recv-keys $MONGO_RELEASE_FINGERPRINT

ENV MONGO_VERSION 2.6.7

RUN curl -SL "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-$MONGO_VERSION.tgz" -o mongo.tgz \
        && curl -SL "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-$MONGO_VERSION.tgz.sig" -o mongo.tgz.sig \
        && gpg --verify mongo.tgz.sig \
        && tar -xvf mongo.tgz -C /usr/local --strip-components=1 \
        && rm mongo.tgz*

COPY mongo-perf /mongo-perf
RUN pip install -r mongo-perf/requirements.txt

VOLUME /data/db

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 27017
CMD ["mongod"]
