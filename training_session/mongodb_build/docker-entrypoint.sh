#!/bin/bash

set -e

chown -R mongodb /data/db

numa='numactl --interleave=all'
if $numa true &> /dev/null; then
	set -- $numa "mongod"
fi

exec gosu mongodb "mongod" --smallfiles &

sleep 5

cd mongo-perf

time1=$(date +"%s")

python benchrun.py -f testcases/* -t 1

time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "$diff\n" >> "/shared_volume/run_time_mongodb"