import json # Used to read values from the config file.
import subprocess # Used to run ZFS commands
from io import StringIO # Used to iterate over the lines of the ZFS output.
import re # Used to format strings for commands.

'''
This script is used to make a complete incremental backup of the contents stored on a primary ZFS storage
server to a secondary backup server. For brevity, these servers will be referred to as "main" and
"backup" within the script and the configuration file. The script should be run on the primary system,
which will connect to the secondary system through SSH.
Before running the script, make sure to create a config.json file in the same directory as this
file. This file should have three key-value pairs with these keys:
    1. main_fsname      (the name of the main filesystem)
    2. backup_fsname    (the name of the backup filesystem)
    3. backup_hostname  (the hostname for the server hosting the backup filesystem)
'''
# First, load the main filesystem's name, the backup filesystem's name, and the hostname of the remote
#     server on which the backup filesystem is hosted. These values are loaded from a config file named config.json
#     stored in the same directory as the backup script.
main_fsname = ""
backup_fsname = ""
backup_hostname = ""
try:
    with open('config.json', 'r') as config:
        config_json = json.load(config)
        if 'main_fsname' not in config_json or 'backup_fsname' not in config_json or 'backup_hostname' not in config_json:
            print("One or more of the required keys not present in config.json")
            print("Required keys: main_fsname, backup_fsname, and backup_hostname")
            exit(1)
        main_fsname = config_json['main_fsname']
        backup_fsname = config_json['backup_fsname']
        backup_hostname = config_json['backup_hostname']
except FileNotFoundError: # If file does not exist
    print("ERROR: Must provide a config.json file with three keys: main_fsname, backup_fsname, and backup_hostname")
    exit(1)
except json.decoder.JSONDecodeError: # If the config file is not a valid json file(eg. empty file, corrupted file)
    print("ERROR: JSON file not formatted correctly.")
    exit(1)
# Gets a list of information about the ZFS pools on the main system.
# Casts the console output to a StringIO object to enable iterating over each line of the output.
pools_list = StringIO(subprocess.run(["zfs", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout)
commands = open("commands_output.txt", "w")
'''
Sample format of pools_list:
NAME                              USED  AVAIL     REFER  MOUNTPOINT
tank                             31.6T  8.36T      222K  /tank
tank/archive                     17.5T  8.36T     7.73T  /tank/archive
tank/archive/aircheck            8.04T  8.36T      205K  /tank/archive/aircheck
tank/archive/aircheck/am         27.7M  8.36T     4.17M  /tank/archive/aircheck/am
tank/archive/aircheck/fm         2.43T  8.36T     2.43T  /tank/archive/aircheck/fm
[redacted]
'''
next(pools_list) # skip the header line
next(pools_list) # skip the base ZFS directory line since trying to back this up causes errors.
# Get a list of all the ZFS snapshots on the main system.
snapshot_list = subprocess.run(["zfs", "list", "-t", "snapshot"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
# Get a list of all the ZFS snapshots on the backup system.
backup_snapshot_list = subprocess.run(["ssh", backup_hostname, "zfs", "list", "-t", "snapshot"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
for line in pools_list: # Iterate over all the lines to back up each ZFS pool.
    current_directory_name = line.split(' ')[0] # Get the first space-separated string on the line, which is the name of the current ZFS pool
    print("ZFS pool name: {}".format(current_directory_name))
    current_directory_search = current_directory_name + "@zfs-auto-snap_weekly" # add weekly snap suffix without date to search for the most recent weekly snapshot
    # These 3 lines retrieve the most recent weekly snapshot for the current ZFS pool on the main system.
    search_for_current_dir = subprocess.run(("grep", current_directory_search), input=snapshot_list.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    get_most_recent_week = subprocess.run(["tail", "-1"], input=search_for_current_dir.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    most_recent_main_snapshot = get_most_recent_week.stdout.split(' ')[0]
    print("\tMost recent main snapshot: {}".format(most_recent_main_snapshot))
    # Change the prefix from the name of the main ZFS filesystem to the name of the backup filesystem.
    backup_directory_name = re.sub(r'^{}'.format(main_fsname), r'{}'.format(backup_fsname), current_directory_name)
    backup_directory_search = re.sub(r'^{}'.format(main_fsname), r'{}'.format(backup_fsname), current_directory_search)
    # These 3 lines get the most recent corresponding snapshot of the current ZFS pool on the backup server.
    search_for_backup_dir = subprocess.run(("grep", backup_directory_search), input=backup_snapshot_list.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    get_most_recent_backup_week = subprocess.run(["tail", "-1"], input=search_for_backup_dir.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    most_recent_backup_snapshot = get_most_recent_backup_week.stdout.split(' ')[0]
    print('\tMost recent backup snapshot: {}'.format(most_recent_backup_snapshot))
    # If the string is empty, that means there's currently no snapshot on the backup server. As a result, run a command to create the pool on the backup.
    if not most_recent_backup_snapshot.strip(): #if string is empty
        subprocess.run("zfs send " + most_recent_main_snapshot + " | ssh " + backup_hostname + " zfs receive -u " + backup_directory_name, shell=True, check=True)
        commands.write("zfs send " + most_recent_main_snapshot + " | ssh " + backup_hostname + " zfs receive -u " + backup_directory_name + "\n")
        print("Created a new pool for {} on the backup server.".format(current_directory_name))
    else: # Perform an incremental backup to only send what has changed between the most recent snapshot on the backup and the most recent snapshot on main.
        # Change the host name of the newest snapshot on the backup server to the main server so that the corresponding snapshot on the host server can be sent.
        older_main_snapshot = re.sub(r'^{}'.format(backup_fsname), r'{}'.format(main_fsname), most_recent_backup_snapshot)
        subprocess.run("zfs send -i " + older_main_snapshot + " " + most_recent_main_snapshot + " | ssh " + backup_hostname + " zfs receive -u -F " +  backup_directory_name, shell=True, check=True)
        commands.write("zfs send -i " + older_main_snapshot + " " + most_recent_main_snapshot + " | ssh " + backup_hostname + " zfs receive -u -F " +  backup_directory_name + "\n")
        print("\tPerformed an incremental backup.")
commands.close()
