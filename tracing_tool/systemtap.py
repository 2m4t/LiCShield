'''
Created on Feb 2, 2015

@author: Massimiliano Mattetti
'''
import os
import subprocess
import time
import distutils.spawn

SYSTEMTAP_SCRIPT = os.path.join(os.path.dirname(__file__), "systemtap_scripts/tracer.stp")
STAP = distutils.spawn.find_executable("stap")
DOCKER = distutils.spawn.find_executable("docker")
DOCKER_DAEMON = DOCKER + " -d"
DOCKER_PID_FILE = "/var/run/docker.pid"

class Systemtap(object):
    
    def __init__(self, trace_file):
        
        self._trace_file = trace_file
        self._cmd = [STAP, "-g", SYSTEMTAP_SCRIPT, "-v", "-c", DOCKER_DAEMON, "-o", trace_file]              
    
    def run(self):
        
        if(os.path.isfile(DOCKER_PID_FILE)):
            print "Error: Docker is already running. Stop it before to run this script."
            return False
        
        '''A negative bufsize means to use the system default, which usually means fully buffered.'''
        '''The default value for bufsize is 0 (unbuffered).'''
        self._process = subprocess.Popen(self._cmd, stderr=subprocess.PIPE, bufsize=-1) 
        print "Running trace command %s" % self._cmd
        
        for line in iter(self._process.stderr.readline, b''):
            print line,
            if "Pass 5: starting run." in line:
                '''wait until the daemon has finished the boot phase'''
                while (not os.path.isfile(DOCKER_PID_FILE)):
                    time.sleep(1)
                return True
            
        return False
    
    def is_running(self):
        
        if(self._process):
            return self._process.poll() == None
        return False
        
    def wait_trace_end(self):
        
        if(self.is_running()):
            old_size = 0
            size = os.path.getsize(self._trace_file)
            while((size - old_size) != 0):
                time.sleep(1)
                old_size = size
                size = os.path.getsize(self._trace_file)
        else:
            raise Exception("Can not wait for the trace end since the tracing script is not running!")
        
    def terminate(self):
        
        if(self.is_running()):
            self._process.terminate()
        
        
