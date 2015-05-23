#!/bin/bash

time1=$(date +"%s")
python benchmark/perf.py -r --benchmarks=2to3 /usr/local/bin/python /usr/local/bin/python
time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "$diff\n" >> "/shared_volume/run_time_python"