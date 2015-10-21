# LiCShield
LiCShield is an open source project to harden the Linux systems running the [Docker](https://github.com/docker/docker) containers. It is made up by a set of Python modules and a bunch of Bash scripts. It relies on the [Python API client library](https://github.com/docker/docker-py) to interact with the Docker daemon. Therefore, make sure you have installed this library on your system.

The [SystemTap](https://sourceware.org/systemtap/) tracing tool version 2.9 ([Step-by-Step Installation Guide](https://github.com/LinuxContainerSecurity/LiCShield/blob/master/SystemTap%202.9%20installation%20guide.txt)) and the [kernel debug symbols](https://yaapb.wordpress.com/2012/12/28/debugging-your-running-kernel-in-ubuntu/) have to be installed in the system to use this software.

LiCShield has been tested with a modified version of Docker running without any AppArmor profile (Docker has been [recompiled](https://docs.docker.com/v1.5/contributing/devenvironment/) with [apparmor_disabled.go](https://github.com/opencontainers/runc/blob/master/libcontainer/apparmor/apparmor_disabled.go) renamed to [apparmor.go](https://github.com/opencontainers/runc/blob/master/libcontainer/apparmor/apparmor.go)).

# How it works
LiCShield generates [AppArmor](http://wiki.apparmor.net/index.php/Main_Page) profiles by tracing the Docker daemon during the execution of the *build* and *run* commands.

To trace the build of a Docker image it is necessary to deploy the relative Dockerfile in a directory whose name must end with *_build*. Then, running as root the **start_build.sh** script, specifing the path to the Dockerfile, the build operation will be executed and the trace file will be available under the path *$HOME/results*.
In the same directory of the trace file it can be found the AppArmor profiles for the Docker daemon and for the container processes. To test these profiles is available the **test_build.sh** script which executes again the build of the image but this time without tracing the operation and enforcing the two profiles. 

As well as for the build operation also for the run one a couple of scripts are available to generate and to test the AppArmor profiles. The names of these script end with *_run.sh* instead of *_build.sh*.
