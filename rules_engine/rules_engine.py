'''
Created on Mar 5, 2015

@author: Massimiliano Mattetti
'''

import os
import codecs
import argparse
from string import Template
from rules_generators import get_permission, glob_container_paths, EXEC_PERMISSION

base_template = Template("""
#include <tunables/global>

$docker_exe flags=(attach_disconnected, mediate_deleted, namespace_relative) {
\t#include <abstractions/base>
\tcapability,
\tnetwork,
\tumount,
\tsignal (send) peer=$child,
\tptrace peer=$child,
\t$docker_home rw,
\t$docker_home** rwkl,
$rules
}
""")

child_template = Template("""
#include <tunables/global>

profile $name flags=(attach_disconnected, mediate_deleted, namespace_relative) {
\t#include <abstractions/base>
\tcapability,
\tnetwork,
\tumount,
\tsignal (receive) peer=$parent_profile,
$rules
 }
""") 

'''Apparmor 2.8.95 doesn't recognize correctly the following mount options sequence'''
APPARMOR_MOUNT_FLAGS_BUG = ["ro", "nosuid", "nodev", "noexec", "remount", "rbind"]

DOCKER_EXE = "/usr/bin/docker"
DOCKER_HOME = "/var/lib/docker/"
CHILD_PROFILE_NAME = "container"

PIVOT_ROOT_PROBE_POINT = "security_sb_pivotroot"
MOUNT_PROBE_POINT = "do_mount" 
LINK_PROBE_POINT = "security_path_link"
RENAME_PROBE_POINT = "security_path_rename"

ERRORS_FILENAME = "%s/%s_errors.txt"
IDS_FILENAME = "%s/%s_ids.txt"
PROFILE_FILENAME = "%s/%s_profile_%s"

host_profile = None
container_profile = None

class Profile():
    def __init__(self, cmd, is_container):
        self._cmd = cmd
        self._is_container = is_container
        self._pivot_root_rule = None
        self._access_rules = {}
        self._execution_rules = set()
        self._link_rules = set()
        self._mount_rules = set()
                 
    def add_access_rule(self, path, permission):
        
        if("m" not in permission):
            ''' write, read and lock permissions already granted 
                under the Docker home directory tree '''
            if (not self._is_container):
                if (path.startswith(DOCKER_HOME)):
                    return
            
            elif (not self._access_rules.has_key(path)) and (not path.endswith("*")):
                path = glob_container_paths(path, self._cmd)
        
        old_permission = self._access_rules.get(path)
        if old_permission:
            if old_permission == permission:
                return
            permission = "".join(set(old_permission + permission))
            ''' resolve conflict between append and write permission '''
            if("a" in permission and "w" in permission):
                permission = permission.replace("a", "")
        self._access_rules[path] = permission      
        
    def add_pivot_root_rule(self, old_root, new_root):
        if(self._pivot_root_rule):
            return
        if(self._is_container):
            self._pivot_root_rule = "pivot_root"
        else:
            self._pivot_root_rule = "pivot_root oldroot=%s %s -> %s" % (old_root, new_root, CHILD_PROFILE_NAME)     
        
    def add_execution_rule(self, process_path):
        exec_rule = "%s %s" % (process_path, EXEC_PERMISSION)
        self._execution_rules.add(exec_rule)
            
    def add_link_rule(self, source, target):
        if (self._is_container):
            source = glob_container_paths(source, self._cmd)
            target = glob_container_paths(target, self._cmd)
        elif(source.startswith(DOCKER_HOME) and target.startswith(DOCKER_HOME)):
            return
        rule = "link %s -> %s" % (target, source)
        self._link_rules.add(rule)
            
    def add_mount_rule(self, ftype, options, source, target):
        mount_rule = "mount"
        
        ''' In case of bugged flags sequence log every 
            mount operation on the target mount point '''
        if(set(options) == set(APPARMOR_MOUNT_FLAGS_BUG)):
            mount_rule = "mount -> %s" % target
        else:  
            if(ftype):
                mount_rule += " fstype=%s" % ftype
        
            if(len(options) > 0):
                mount_rule += " options=(%s)" % ",".join(options) 
                
            if(source):
                mount_rule += " %s" % source
                
            mount_rule += " -> %s" % target

        self._mount_rules.add(mount_rule)
    
    def __str__(self):
        rules = ""
            
        if(self._pivot_root_rule):
            rules = "\t%s,\n" % self._pivot_root_rule
            
        for mount_rule in self._mount_rules:
            rules += "\t%s,\n" % mount_rule
            
        for exec_rule in self._execution_rules:
            rules += "\t%s,\n" % exec_rule
            
        for link_rule in self._link_rules:
            rules += "\t%s,\n" % link_rule
            
        for (path, permission) in self._access_rules.iteritems():
            rules += "\t%s %s,\n" % (path, permission) 
            
        return rules            
        
        
def update_profiles(line):
    (probe_point, layer_id, executable_path, permission_tuple, root_mnt_point) = get_permission(line)
    
    if(probe_point == None):
        return None
    
    preamble = "%s %s %s" % (probe_point, layer_id, executable_path)
    
    if(root_mnt_point == "/"):
        profile = host_profile
    else:
        profile = container_profile
    
    profile.add_execution_rule(executable_path)
    
    if(probe_point == PIVOT_ROOT_PROBE_POINT):
        (old_root, new_root) = permission_tuple
        profile.add_pivot_root_rule(old_root, new_root)   
        return "%s %s %s" % (preamble, old_root, new_root)
    
    if(probe_point == LINK_PROBE_POINT):
        (source, target) = permission_tuple
        profile.add_link_rule(source, target)
        return "%s %s %s" % (preamble, source, target)

    if(probe_point == MOUNT_PROBE_POINT):
        (ftype, options, source, target) = permission_tuple
        profile.add_mount_rule(ftype, options, source, target)
        return "%s %s %s" % (preamble, source, target)
    
    if(probe_point == RENAME_PROBE_POINT):
        (old_path, old_path_permission, new_path, new_path_permission) = permission_tuple
        profile.add_access_rule(old_path, old_path_permission)
        profile.add_access_rule(new_path, new_path_permission)
        return "%s %s %s" % (preamble, old_path, new_path)
    
    (path, permission) = permission_tuple
    if(permission == EXEC_PERMISSION):
        profile.add_execution_rule(path)
    else:
        profile.add_access_rule(path, permission)
    return "%s %s" % (preamble, path)
    
    
def generate_profiles(args):
    global host_profile
    global container_profile
    
    if not os.path.isfile(args.trace_file):
        print "%s file not found" % args.trace_file
        exit (-1)
    
    if not os.path.exists(args.profile_dir):
        os.makedirs(args.profile_dir)
        
    host_profile = Profile(args.cmd, False)
    container_profile = Profile(args.cmd, True)
    
    errors_file = ERRORS_FILENAME % (args.profile_dir, args.cmd)
    ids_file = IDS_FILENAME % (args.profile_dir, args.cmd)
    
    ids_data = set()
    with codecs.open(args.trace_file, "r", "utf-8") as trace:
        with codecs.open(errors_file, "w", "utf-8") as error:
            for line in trace:
                res = update_profiles(line)
                if res:
                    ids_data.add(res)
                else:
                    error.write(line + os.linesep)
                            
    with codecs.open(ids_file, "w", "utf-8") as ids:
        for line in ids_data:
            ids.write(line + os.linesep)
    
    parent_file_name = PROFILE_FILENAME % (args.profile_dir, args.cmd, "host")
    with codecs.open(parent_file_name, "w", "utf-8") as profile:
        profile.write(base_template.substitute(docker_exe=DOCKER_EXE, child=CHILD_PROFILE_NAME, docker_home=DOCKER_HOME, rules=host_profile))
    
    child_file_name = PROFILE_FILENAME % (args.profile_dir, args.cmd, CHILD_PROFILE_NAME)
    with codecs.open(child_file_name, "w", "utf-8") as child_profile:
        child_profile.write(child_template.substitute(name=CHILD_PROFILE_NAME, parent_profile=DOCKER_EXE, rules=container_profile))


parser = argparse.ArgumentParser(description="Generate AppArmor profile.")
parser.add_argument("trace_file", help="full path to trace file")
parser.add_argument("cmd", choices=["build", "run"], help="Docker command used to generate the trace")
parser.add_argument("profile_dir", help="directory where to save the AppArmor profile")
parser.set_defaults(func=generate_profiles)

def main():
    args = parser.parse_args()
    args.func(args)

if  __name__ == "__main__":
    main()
    
