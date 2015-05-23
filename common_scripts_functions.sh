#!/bin/bash

function clean_docker_containers {

	start_docker

	echo -e "\nRemoving all running containers:"
	docker ps -a |  grep -v 'CONTAINER' | awk '{print $1}' | while read id; do
	    docker stop $id &>/dev/null
	    docker rm -f $id 
	done
	echo "Done."

	if [ $# -eq 1 ]; then
		regex="^<none>\|^$1"
	else
		regex="^<none>"
	fi

	echo -e "\nDeleting all cached layers except the base:"
	docker images | grep -e $regex | awk '{print $3}' | while read id; do
	    docker rmi -f $id 
	done
	echo "Done."
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

	base_image=$(egrep "^FROM" "$1/Dockerfile" | awk -F'FROM ' '{print $2}')
	echo -e "\nPulling image $base_image"
	docker pull $base_image
	echo "Done."
}
