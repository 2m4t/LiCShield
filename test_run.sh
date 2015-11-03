#!/bin/bash

if [ $(id -u) != 0 ]; then
   echo -e "\nThis script must be run as root\n" 1>&2
   exit 1
fi

if [ $# -ne 1 ]; then
    echo -e "\nUsage: $0 path_to_build_directoy\n" 1>&2
    exit 1 
fi

while true; do
    read -p "Do you wish to apply the run profiles? " yn
    case $yn in
        [Yy]* ) answer="yes"; break;;
        [Nn]* ) answer="no"; break;;
        * ) echo "Please answer yes or no.";;
    esac
done

script_dir=$(cd "$( dirname "$BASH_SOURCE[0]" )" && pwd)

export PYTHONPATH="$script_dir"

source "$script_dir/common_scripts_functions.sh"

build_path=$(cd "$1" && pwd)

check_dir "$build_path"
check_file_in_directory "$build_path" "Dockerfile" 

build_dir=$(basename $build_path)

image_name=${build_dir//_build/}
tag="${image_name}:test"
test_dir="$HOME/results/${image_name}_test_0"
check_dir "$test_dir"

output_dir="${HOME}/results"
mkdir -p "$output_dir"

if [ $answer == "yes" ]; then
	check_file_in_directory "$test_dir" "run_profile_host"
	host_profile="$test_dir/run_profile_host"

	check_file_in_directory "$test_dir" "run_profile_container"
	container_profile="$test_dir/run_profile_container"
	
	stop_docker

	apply_profiles "$host_profile" "$container_profile"

fi

if [ $image_name == "nginx" -o $image_name == "php" -o $image_name == "nodejs" ]; then
	"$script_dir/httperf_workload.sh" $image_name &
fi

period=300 # 5 minutes

start_docker

echo -e "\nSTART RUNNING CONTAINER $tag (for $period s)"

python "$script_dir/training_session/docker_client.py" "run" "$tag" "--period" "$period"

if [ $? -ne 0 ]; then
    echo -e "\nError: the run of image $image_name failed\n" 1>&2
    
	if [ $answer == "yes" ]; then
		remove_profiles "$host_profile" "$container_profile"

	fi

	stop_docker
	clean_docker_containers 
    exit 1
fi
echo -e "\n$image_name container run completed!"

if [ $answer == "yes" ]; then
	remove_profiles "$host_profile" "$container_profile"
fi

stop_docker