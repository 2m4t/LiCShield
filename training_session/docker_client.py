'''
Created on Mar 16, 2015

@author: Massimiliano Mattetti
'''

import os
import time
import argparse
import json
from docker import Client


def open_connection():
    return Client(base_url="unix://var/run/docker.sock")
 
   
def print_dic(data):
    if type(data) is not dict:
        print data
    else:
        for v in data.values():
            print_dic(v)


def build(build_directory, tag):
    cli = open_connection()
    for line in cli.build(path=build_directory, tag=tag, rm=True):
        data = json.loads(line)
        if(type(data) is dict): 
            if(data.has_key("stream")):
                print data["stream"],
            elif data.has_key("error"):
                print data["error"]
                exit(-1)
            else:
                print_dic(data)
            
            
def run(image):
    cli = open_connection()
    container = cli.create_container(image, detach=True, ports=[80], volumes=["/shared_volume"])
    cli.start(container, port_bindings={80: 8080}, cap_add=["dac_read_search"], binds={"/shared_volume": {"bind": "/shared_volume", "ro": False}})
    return container


def stop(container):
    cli = open_connection()
    cli.stop(container)


parser = argparse.ArgumentParser(description="Docker commands wrapper")

subparsers = parser.add_subparsers(help="Docker commands")

build_parser = subparsers.add_parser("build", help="build a Docker image from a Dockerfile")
build_parser.add_argument("build_directory", help="path to the directory containing the Dockerfile")
build_parser.add_argument("tag", help="repository name (and optionally a tag) to be applied to the resulting image in case of success")


run_parser = subparsers.add_parser("run", help="run a Docker container from image")
run_parser.add_argument("image", help="name of the image to run")
run_parser.add_argument("--period", dest="period", default=30, type=int, help="wait a period of time (in seconds) after a container run [Default: %(default)s]")
        
    
def main():
    if os.geteuid() != 0:
        print "This script requires root privileges"
        exit(-1)
    args = parser.parse_args()
    if hasattr(args, "build_directory"):
        build(args.build_directory, args.tag)
    else:
        container = run(args.image)
        time.sleep(args.period)
        stop(container)
    
if __name__ == "__main__":
    main()
