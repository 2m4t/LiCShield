# LiCShield
LiCShield is an open source project to harden the Linux systems running [Docker](https://github.com/docker/docker) containers (tested with Docker version 1.6.x). 

The [Python API client library](https://github.com/docker/docker-py) is used to interact with the Docker daemon, therefore this library has to be installed on the system to make LiCShield work properly.

The [SystemTap](https://sourceware.org/systemtap/) tracing tool version 2.9 ([Step-by-Step Installation Guide](https://github.com/LinuxContainerSecurity/LiCShield/blob/master/SystemTap%202.9%20installation%20guide.txt)) and the [kernel debug symbols](https://yaapb.wordpress.com/2012/12/28/debugging-your-running-kernel-in-ubuntu/) have to be installed in the system to use this software.

LiCShield has been tested with a modified version of Docker running without any AppArmor profile (Docker has been [recompiled](https://docs.docker.com/v1.5/contributing/devenvironment/) with [apparmor_disabled.go](https://github.com/opencontainers/runc/blob/master/libcontainer/apparmor/apparmor_disabled.go) renamed to [apparmor.go](https://github.com/opencontainers/runc/blob/master/libcontainer/apparmor/apparmor.go) and the [build constraint](https://golang.org/pkg/go/build/) changed to make the compilation succeed).

# How it works
LiCShield generates [AppArmor](http://wiki.apparmor.net/index.php/Main_Page) profiles by tracing the Docker daemon during the execution of the *build* and *run* commands.

To trace the build of a Docker image it is necessary to deploy the relative Dockerfile in a directory whose name must end with *_build*. The **start_build.sh** script, executed with root credentials and specifing the path to the Dockerfile, builds the image and generates a trace file under the path *$HOME/results*.
In the same directory of the trace file it can be found the AppArmor profiles for the Docker daemon and for the container processes. To test these profiles is available the **test_build.sh** script which executes again the build of the image, but this time enforcing the two AppArmor profiles and skipping the tracing phase.

As well as for the build also for the run operation are available a couple of scripts to generate and test AppArmor profiles. The names of these script end with *_run.sh* instead of *_build.sh*.
