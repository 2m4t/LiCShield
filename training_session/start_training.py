'''
Created on Feb 2, 2015

@author: Massimiliano Mattetti
'''

import os
import time
import argparse
import traceback
from tracing_tool import systemtap
from training_session import docker_client


def docker_run(args, stap):
    if stap.run():
        container = docker_client.run(args.image)
        time.sleep(args.period)
        stap.terminate()
        docker_client.stop(container)
    else:
        exit(-1)
    
    
def docker_build(args, stap):
    if stap.run():
        if os.path.isdir(args.build_directory):
            if os.path.exists("%s/Dockerfile" % args.build_directory):
                docker_client.build(args.build_directory, args.tag)
                stap.wait_trace_end()
                stap.terminate()
            else:
                parser.error("there is not Dockerfile in %s " % os.path.abspath(args.dir))
        else:
            parser.error("directory %s does not exist " % os.path.abspath(args.dir))
    else:
        exit(-1)
        

parser = argparse.ArgumentParser(description="Docker commands wrapper")
parser.add_argument("trace_file", help="file of the system calls trace")

subparsers = parser.add_subparsers(help="Docker commands")

build_parser = subparsers.add_parser("build", help="build a Docker image from a Dockerfile")
build_parser.add_argument("build_directory", help="path to the directory containing the Dockerfile")
build_parser.add_argument("tag", help="repository name (and optionally a tag) to be applied to the resulting image in case of success")
build_parser.set_defaults(func=docker_build)


run_parser = subparsers.add_parser("run", help="run a Docker container from image")
run_parser.add_argument("image", help="name of the image to run")
run_parser.add_argument("--period", dest="period", default=30, type=int, help="wait a period of time (in seconds) after a container run [Default: %(default)s]")
run_parser.set_defaults(func=docker_run)
        
        
def main():
    if os.geteuid() != 0:
        print "This script requires root privileges"
        exit(-1)
    args = parser.parse_args()
    stap = systemtap.Systemtap(args.trace_file)
    try:
        args.func(args, stap)
    except Exception:
        stap.terminate()
        print traceback.format_exc()
        exit(-1)
    
if __name__ == "__main__":
    main()
