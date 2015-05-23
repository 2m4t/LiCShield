#!/bin/bash

httperf -v >/dev/null 2>&1

if [ $? -ne 0 ]; then
	echo -e "httperf is not installed in the system.\nNo workload will be generated for the test.\n"
	exit 1
fi

echo -e "\nWaiting server start-up before to run httperf benchmark"
nc -z 0.0.0.0 8080
slept=2
while [ $? != 0 ]; do
	sleep 2
	slept=$(( $slept + 2 ))
	nc -z 0.0.0.0 8080
done
sleep 2
echo -e "\nServer ready after $slept seconds"

if [ $# -eq 1 ]; then
	output_file="${HOME}/run_time_$1"
else
	output_file="/dev/null"
fi

echo -e "Run httperf benchmark"
httperf --hog --server=0.0.0.0 --port=8080 --num-conn 30000 --ra 100 --timeout 10 | tee "$output_file"
echo -e "httperf benchmark completed!\n"