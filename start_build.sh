#!/bin/bash

time1=$(date +"%s")

if [ $(id -u) != 0 ]; then
   echo -e "\nThis script must be run as root\n" 1>&2
   exit 1
fi

if [ $# -ne 1 ]; then
    echo -e "\nUsage: $0 path_to_directoy\n" 1>&2
    exit 1 
fi

script_dir=$(cd "$( dirname "$BASH_SOURCE[0]" )" && pwd)

export PYTHONPATH="$script_dir"

source "$script_dir/common_scripts_functions.sh"

build_path=$(cd "$1" && pwd)

check_dir "$build_path"
check_file_in_directory "$build_path" "Dockerfile" 

build_dir=$(basename $build_path)

image_name=${build_dir//_build/}
tag="${image_name}:test"
results_dir="$HOME/results"

for i in seq 9 -1 0; do
	dir1="$results_dir/${image_name}_test_$i"
	dir2="$results_dir/${image_name}_test_$(($i + 1))"
	if [ -d $dir1 ]; then
		mv $dir1 $dir2
	fi
done

test_dir="$results_dir/${image_name}_test_0"
mkdir -p "$test_dir"

clean_docker_containers $image_name

# build phase

trace_file="$test_dir/build_trace.txt"

stop_docker

echo -e "\nSTART BUILD IMAGE $image_name\n"

python "$script_dir/training_session/start_training.py" "$trace_file" "build" "$build_path" "$tag"

if [ $? -ne 0 ]; then
    echo -e "\nError: the build of $image_name failed" 1>&2
	clean_docker_containers $image_name
	stop_docker
    exit 1
fi

stop_docker

echo -e "\nImage $image_name built"

echo -e "\nGenerating profile from build trace"

python "$script_dir/rules_engine/rules_engine.py" "$trace_file" "build" "$test_dir"

if [ $? -ne 0 ]; then
    echo -e "\nError: profile generation failed for build\n" 1>&2
	clean_docker_containers $image_name
    exit 1
fi
echo "Done."

time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "$image_name build $diff\n" >> "$test_dir/time"