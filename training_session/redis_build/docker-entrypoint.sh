#!/bin/bash
set -e

if [ "$1" = 'redis-server' ]; then
	chown -R redis .
	gosu redis "$@" &
	sleep 2
	time1=$(date +"%s")
	redis-benchmark -q
	time2=$(date +"%s")
	diff=$(($time2-$time1))
	echo -e "$diff\n" >> "/shared_volume/run_time_redis"
fi
