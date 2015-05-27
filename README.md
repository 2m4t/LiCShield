# LiCShield
LiCShield is an open source project to harden the Linux systems running the [Docker](https://github.com/docker/docker) containers. It is made up by a set of Python modules and a bunch of Bash scripts. 

The [SystemTap](https://sourceware.org/systemtap/) tracing tool has to be installed in the system to use this software.


# How it works
LiCShield generates [AppArmor](http://wiki.apparmor.net/index.php/Main_Page) profiles by tracing the Docker daemon during the execution of the *build* and *run* commands.

To trace the build of a Docker image it is necessary to deploy the relative Dockerfile in a directory whose name must end with *_build*. Then, running as root the **start_build.sh** script, specifing the path to the Dockerfile, the build operation will be executed and the trace file will be available under the path *$HOME/results*.
In the same directory of the trace file it can be found the AppArmor profiles for the Docker daemon and for the container processes. To test these profiles is available the **test_build.sh** script which executes again the build of the image but this time without tracing the operation and enforcing the two profiles. 

As well as for the build operation also for the run one a couple of scripts are available to generate and to test the AppArmor profiles. The names of these script end with *_run.sh* instead of *_build.sh*.
