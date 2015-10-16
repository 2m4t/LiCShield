'''
Created on Mar 5, 2015

@author: Massimiliano Mattetti
'''
import re
import json
import os

class Glob_Patterns():
    def __init__(self, glob_dict):
        self.__dict__ = glob_dict


glob_patterns = None
if not glob_patterns:
    rule_engine_dir = os.path.dirname(os.path.realpath(__file__))
    with open(rule_engine_dir + "/glob_patterns_rules.json") as gb_file:
        glob_dict = json.load(gb_file)
    glob_patterns = Glob_Patterns(glob_dict)
    
EXEC_PERMISSION = "ix"

MS_REC = 16384
MS_PRIVATE = (1 << 18)
MS_BIND = 4096
MS_REMOUNT = 32

MOUNT_FLAGS_LIST = [(1, "ro"), (2, "nosuid"), (4, "nodev"), (8, "noexec"), (16, "sync"),
                    (MS_REMOUNT, "remount"), (128, "dirsync"), (1024, "noatime"), (2048, "diratime"),
                    (MS_BIND, "bind"), (8192, "move"), (32768, "silent"), ((1 << 24), "strictatime"),
                    (MS_PRIVATE, "make-private")]


def get_layer(cgorup):
    if("docker" not in cgorup):
        return "host"
    return cgorup.split("/docker/")[1]


def replace_container_id(path):
    return re.sub(glob_patterns.container_id, "*", path)


def glob_paths(path):
    path = replace_container_id(path)
    for (regex, sub_value) in glob_patterns.glob_patterns_regex.iteritems():
        path = re.sub(regex, sub_value, path)
    return path


def glob_container_paths(path, cmd):
    full_access_paths = glob_patterns.container_full_access_paths
    if cmd == "build":
        full_access_paths += glob_patterns.container_build_full_access_paths
    
    if (path.startswith(glob_patterns.container_root)):
        for container_path in full_access_paths:
            if re.match(glob_patterns.container_root + "\*"  + container_path + ".+", path):
                return glob_patterns.container_root + "*" + container_path + "**"
    else:
        for container_path in full_access_paths:
            if re.match(container_path + ".+", path):
                return container_path + "**"
    return path


def open_permission_rule(args):
    args_list = args.split()
    square_args = re.findall("\{(.*?)\}", args)
    flags = int(args_list[0])
    
    ''' FMODE_EXEC flag: File is opened for execution with sys_execve '''
    if(flags & 32):
        return ((replace_container_id(square_args[0]), EXEC_PERMISSION), square_args[-1])
    
    path = glob_paths(square_args[0])
    
    accmode = flags & 3
    
    ''' O_APPEND '''
    if(flags & 8192):
        new_permission = "a"
        if(accmode == 2 or accmode == 0):
            new_permission += "r"
    else:
        if(accmode == 2):
            new_permission = "rw"
        elif(accmode == 1):
            new_permission = "w"
        else:
            new_permission = "r"
    
    return ((path, new_permission), square_args[-1])


def memory_map_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    path = replace_container_id(square_args[0])
    return ((path, "m"), square_args[-1]) 
 
        
def write_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    return ((glob_paths(square_args[0]), "w"), square_args[1])


def read_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    return ((glob_paths(square_args[0]), "r"), square_args[-1])


def rw_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    return ((glob_paths(square_args[0]), "rw"), square_args[-1])


def lock_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    return ((glob_paths(square_args[0]), "k"), square_args[-1])


def rename_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    old_path = glob_paths(square_args[0])
    new_path = glob_paths(square_args[1])
    return ((old_path, "rw", new_path, "rw"), square_args[-1])
        

def pivot_root_link_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    path1 = glob_paths(square_args[0])
    path2 = glob_paths(square_args[1])
    return ((path1, path2), square_args[-1])


def mount_permission_rule(args):
    square_args = re.findall("\{(.*?)\}", args)
    flags = int(square_args[3])
    ftype = None
    source = None
    options = []
    
    if(flags > 0):
        options = [apparmor_mnt_flag for (mnt_flag, apparmor_mnt_flag) in MOUNT_FLAGS_LIST if(mnt_flag & flags)]
        
        if(MS_REC & flags):
            if(MS_PRIVATE & flags):
                options.remove("make-private") 
                options.append("make-rprivate")
            if(MS_BIND & flags):
                options.remove("bind")
                options.append("rbind")
    
    if((len(square_args[2]) > 0) and 
       (square_args[2] != "bind") and 
       (square_args[2] != "none") and
       (not (MS_REMOUNT & flags))):
        ftype = square_args[2]
        
    if((len(square_args[0]) > 0) and
       (not (MS_REMOUNT & flags))):
        source = glob_paths(square_args[0])
        if(source[0] == "/" and source[-1] != '/'):
            source = "%s/" % source
    
    target = glob_paths(square_args[1])
    if(target[-1] != '/'):
        target = "%s/" % target
    
    return ((ftype, options, source, target), square_args[-1])


def get_permission(line):
    args = line.split(" ", 2)
    probe_point = args[0]
    layer_id = get_layer(args[1])
    square_args = re.findall("\{(.*?)\}", args[2])
    executable_path = replace_container_id(square_args[0])
    if not probe_point_dispatcher.has_key(probe_point):
        return (None, None, None, None, None)
    other_args = line.split("{%s} " % square_args[0], 1)[1]
    (permission_tuple, root_mnt_point) = probe_point_dispatcher[probe_point](other_args)
    return (probe_point, layer_id, executable_path, permission_tuple, root_mnt_point)
    

probe_point_dispatcher = {
                "security_file_open" : open_permission_rule,
                "security_path_symlink" : write_permission_rule,
                "security_path_unlink" : write_permission_rule,
                "security_path_mkdir" : write_permission_rule,
                "security_path_rmdir" : write_permission_rule,
                "security_path_mknod" : rw_permission_rule,
                "security_sb_pivotroot" : pivot_root_link_permission_rule,
                "security_path_link" : pivot_root_link_permission_rule,
                "security_path_rename" : rename_permission_rule,
                "security_path_truncate" : write_permission_rule,
                "security_file_lock" : lock_permission_rule,
                "security_mmap_file" : memory_map_permission_rule,
                "security_file_mprotect" : memory_map_permission_rule,
                "do_mount" : mount_permission_rule,
                "security_path_chroot" : read_permission_rule,
                "security_path_chmod" : write_permission_rule,
                "security_path_chown" : write_permission_rule
                }
