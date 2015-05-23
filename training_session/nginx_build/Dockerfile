FROM debian:jessie

ENV DEBIAN_FRONTEND noninteractive

MAINTAINER NGINX Docker Maintainers "docker-maint@nginx.com"

#RUN apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62

COPY nginx.gpg /
RUN apt-key add /nginx.gpg && rm /nginx.gpg

RUN echo "deb http://nginx.org/packages/mainline/debian/ jessie nginx" >> /etc/apt/sources.list

ENV NGINX_VERSION 1.9.0-1~jessie

RUN apt-get update && \
    apt-get install -y ca-certificates nginx=${NGINX_VERSION} && \
    rm -rf /var/lib/apt/lists/*

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

VOLUME ["/var/cache/nginx"]

COPY helloworld /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]