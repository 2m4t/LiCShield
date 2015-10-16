#!/bin/bash

function clean_docker_containers {

	start_docker

	echo -e "\nRemoving all running containers:"
	docker ps -a |  grep -v 'CONTAINER' | awk '{print $1}' | while read id; do
	    docker stop $id &>/dev/null
	    docker rm -f $id 
	done
	echo "Done."

	echo -e "\nDeleting all cached layers except the base:"
	docker images | grep -e "^<none>\|^$1" | awk '{print $3}' | while read id; do
	    docker rmi -f $id 
	done
	echo "Done."

	stop_docker
}

function start_docker {

	echo -e "\nStarting Docker"
	if [ -f "/run/docker.pid" ]; then
		cat "/run/docker.pid" | ( read pid
			ps -p $pid
		)
		if [ $? -eq 1 ]; then
			rm -f "/run/docker.*" 
		    docker -d  &>/dev/null &
		    sleep 2
		fi
	else
		docker -d  &>/dev/null &
		sleep 2
	fi
	echo "Done."
}

function stop_docker {

	echo -e "\nStopping Docker"

	status=$(timeout 2 service docker status)
	exit_status=$?
	status=$(echo $status | awk -F'/' '{print $1}')
	if [ $exit_status != 124 -a "$status" == "docker start" ]; then
	    service docker stop
	elif [ -f "/var/run/docker.pid" ]; then
		cat /var/run/docker.pid | (
			read pid
			ps -p $pid &>/dev/null
			if [ $? -eq 0 ]; then
				kill -SIGINT $pid
			fi
		)
	fi
	sleep 2
	rm -f "/run/docker.pid"
	rm -f "/run/docker.sock"
	echo "Done."
}

function check_dir {
	if [ ! -d "$1" ]; then
		echo -e "\n$1 is not a valid directory\n" 1>&2
		exit 1
	fi
}

function check_file_in_directory {
	if [ ! -f "$1/$2" ]; then
	    echo -e "\n$2 not found in $1\n" 1>&2
	    exit 1
	fi
}

function apply_profiles {
	echo -e "\nApplying profile $1"
	apparmor_parser -r "$1"
	if [ $? -ne 0 ]; then
	    echo -e "\nError: parsing of profile $1 failed\n" 1>&2
	    exit 1
	fi
	echo "Done."

	echo -e "\nApplying profile $2"
	apparmor_parser -r "$2"
	if [ $? -ne 0 ]; then
		apparmor_parser -R $1
	    echo -e "\nError: parsing of profile $2 failed\n" 1>&2
	    exit 1
	fi
	echo "Done."
}

function remove_profiles {
	echo -e "\nRemove profile $1"
	apparmor_parser -R "$1"
	echo "Done."

	echo -e "\nRemove profile $2"
	apparmor_parser -R "$2"
	echo "Done."
}

function pull_image {
	
	start_docker

	base_image=$(head -1 "$1/Dockerfile" | awk -F'FROM ' '{print $2}')
	echo -e "\nPulling image $base_image"
	docker pull $base_image
	echo "Done."

	stop_docker
}

if [ $(id -u) != 0 ]; then
   echo -e "\nThis script must be run as root\n" 1>&2
   exit 1
fi

if [ $# -gt 2 ]; then
    echo -e "\nUsage: $0 path_to_build_directoy [use_profile]\n" 1>&2
    exit 1 
fi

build_path=$(cd "$1" && pwd)

check_dir "$build_path"
check_file_in_directory "$build_path" "Dockerfile" 

script_dir=$(cd "$( dirname "$BASH_SOURCE[0]" )" && pwd)

export PYTHONPATH="$script_dir"

build_dir=$(basename $build_path)

image_name=${build_dir//_build/}
tag="${image_name}:test"
test_dir="$HOME/results/${image_name}_test_0"
check_dir "$test_dir"

output_dir="${HOME}/results"
mkdir -p "$output_dir"

clean_docker_containers $image_name

# build phase

echo -e "\nSTART BUILD IMAGE $image_name"

if [ $# -eq 2 ]; then
	output_dir="$output_dir/with_profiles"
	mkdir -p "$output_dir"

	check_file_in_directory "$test_dir" "build_profile_host"
	host_profile="$test_dir/build_profile_host"

	check_file_in_directory "$test_dir" "build_profile_container"
	container_profile="$test_dir/build_profile_container"

	apply_profiles "$host_profile" "$container_profile"
else
	output_dir="$output_dir/without_profiles"
	mkdir -p "$output_dir"
fi

pull_image $build_path

start_docker

time1=$(date +"%s")
python "$script_dir/training_session/docker_client.py" "build" "$build_path" "$tag"

if [ $? -ne 0 ]; then
    echo -e "\nError: the build of $image_name failed\n" 1>&2

	if [ $# -eq 2 ]; then
		remove_profiles "$host_profile" "$container_profile"
	fi

    stop_docker
	clean_docker_containers
    exit 1
fi

time2=$(date +"%s")
diff=$(($time2-$time1))
echo -e "\nImage $image_name built in $diff seconds"
echo "$image_name $diff" >> "$output_dir/build_time_$image_name"

if [ $# -eq 2 ]; then
	remove_profiles "$host_profile" "$container_profile"
fi

# run phase

stop_docker

period=3000 # 50 minutes

echo -e "\nSTART RUNNING CONTAINER $tag (for $period s)"

if [ $# -eq 2 ]; then
	check_file_in_directory "$test_dir" "run_profile_host"
	host_profile="$test_dir/run_profile_host"

	check_file_in_directory "$test_dir" "run_profile_container"
	container_profile="$test_dir/run_profile_container"

	apply_profiles "$host_profile" "$container_profile"
fi

start_docker

if [ $image_name == "nginx" -o $image_name == "php" -o $image_name == "nodejs" ]; then
	"$script_dir/httperf_workload.sh" $image_name &
fi

python "$script_dir/training_session/docker_client.py" "run" "$tag" "--period" "$period"

if [ $? -ne 0 ]; then
    echo -e "\nError: the run of image $image_name failed\n" 1>&2
	if [ $# -eq 2 ]; then
		remove_profiles "$host_profile" "$container_profile"
	fistop_docker
	clean_docker_containers 
    exit 1
fi
echo -e "\n$image_name container run completed!"

if [ $# -eq 2 ]; then
	remove_profiles "$host_profile" "$container_profile"
fi

stop_docker

echo -e "\nCLEAN ENVIRONMENT AFTER TEST"
clean_docker_containers $image_name
