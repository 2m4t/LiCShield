#!/bin/bash

script_dir=$(cd "$( dirname "$BASH_SOURCE[0]" )" && pwd)

export PYTHONPATH="$script_dir"

source "$script_dir/common_scripts_functions.sh"

time1=$(date +"%s")

if [ $(id -u) != 0 ]; then
   echo -e "\nThis script must be run as root\n" 1>&2
   exit 1
fi

if [ $# -ne 1 ]; then
    echo -e "\nUsage: $0 path_to_directoy\n" 1>&2
    exit 1 
fi

build_path=$(cd "$1" && pwd)

check_dir "$build_path"
check_file_in_directory "$build_path" "Dockerfile" 

build_dir=$(basename $build_path)

image_name=${build_dir//_build/}
tag="${image_name}:test"
results_dir="$HOME/results"
test_dir="$results_dir/${image_name}_test_0"

check_dir "$test_dir"
trace_file="$test_dir/run_trace.txt"

if [ $image_name == "nginx" -o $image_name == "php" -o $image_name == "nodejs" ]; then
  "$script_dir/httperf_workload.sh" &
fi

stop_docker

period=30

echo -e "\nSTART RUNNING CONTAINER $tag (for $period s)"

python "$script_dir/training_session/start_training.py" "$trace_file" "run" "$tag" "--period" "$period"

if [ $? -ne 0 ]; then
    echo -e "\nError: the run of image $tag failed\n" 1>&2
    clean_docker_containers
    exit 1
fi
echo "Done."

echo -e "\nGenerating profile from run trace"

python "$script_dir/rules_engine/rules_engine.py" "$trace_file" "run" "$test_dir"

if [ $? -ne 0 ]; then
    echo -e "\nError: profile generation failed for run\n" 1>&2
    clean_docker_containers
    exit 1
fi
echo "Done."

time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "$image_name run $diff\n" >> "$test_dir/time"

stop_docker