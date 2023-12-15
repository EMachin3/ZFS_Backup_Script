# ZFS_Backup_Script
This script is used to make a complete incremental backup of the contents stored on a primary ZFS storage server to a secondary backup server. For brevity, these servers will be referred to as "main" and "backup" within the script and the configuration file. The script should be run on the primary system, which will connect to the secondary system through SSH.    

# Instructions    
1. Clone the repository onto the main server.    
2. Create a file named config.json in the repository directory. You may create a copy of config_example.json. Make sure to change all three fields to match your own setup. See the "config.json" section for a detailed description of what is needed.    
3. Make sure that the main server has permissions to remotely connect to the backup server. Additionally, the user accounts on the main server and the backup server must have the necessary permissions to run the "zfs send" and "zfs receive" commands.
4. Once everything is set up, remotely connect to the main server and run this command: python3 backup.py

# config.json    
Before running the script, make sure to create a config.json file in the same directory as backup.py. This file should have three key-value pairs with these keys:    
    1. main_fsname      (the name of the main filesystem)    
    2. backup_fsname    (the name of the backup filesystem)    
    3. backup_hostname  (the hostname for the server hosting the backup filesystem)    

# Disclaimer    
While I have done my best to test this program using two physical ZFS servers, I can not guarantee that this program will always function properly. This program is provided as-is, and I am not responsible for any issues that may occur as a result of running this script on your own setup.    
