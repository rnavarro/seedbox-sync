#!/usr/bin/python

# DETAILS:
# This script is designed to push newly downloaded files from a seedbox (offshore, local on your network, or even local on the same machine) to a target machine or directory.
# It does this by polling the directory (locally) every 10 seconds for new downloads and once found will establish a rsync connection to push them to the target.
# Pushed files are logged in a SQLite database so they are not pushed again the next time the source directory is checked.
# The main advantage verses a plain old rsync script is the target directory can have files deleted from it while the source can continue seeding the files that were deleted on the target.
#
# INSTRUCTIONS:
# Run this script on your seedbox in the background using:
# ./seedbox-sync.py --verbose --progress --times /tmp/a/ /tmp/b/ &
# All parameters except the last two are optional and the trailing "&" will make bash run it in the background.
# The above example will sync files and directories from "/tmp/a/" to "/tmp/b/". If a file is later deleted from "/tmp/b/" it will never be resynced.
# The list of known files is kept in the seedbox-sync.sqlite file which is created at first run.
# IMPORTANT: Make sure the source directory is your torrent client's "completed" directory and not "incomplete" or regular download directory (see "moving files to another directory once complete") otherwise the sync will begin before the file has fully downloaded.
#
# EXAMPLE 1:
# ./seedbox-sync.py --progress /opt/deluge-complete/ john@home.dyndns.com:~/downloads/
# Running on a co-located seedbox, the Deluge client is set to copy completed files to /opt/deluge-complete/.
# After a download is complete the new file or directory will be copied to your home machine using SSH.
# All that is required here is on your home machine adding a user john, then creating a downloads directory for him in his home directory.
#
# EXAMPLE 2:
# ./seedbox-sync.py --verbose --progress --times /tmp/a/ /tmp/b/ &
# Sync all files from /tmp/a/ to /tmp/b/ where /tmp/a/ is the source where your torrent client saves completed files to and /tmp/b/ is the target where the downloads will be mirrored to.
# The above example is using this script as a local sync on the same machine which is still useful because you then can delete downloads from your mirrored target directory and still remain seeding on your torrent client.

import sqlite3
import os
import sys
import subprocess
from time import sleep

if len(sys.argv)<3:
 print("Please run with atleast two parameters.")
 exit(1)

sourceDir=sys.argv[-2].rstrip("/")
destDir=sys.argv[-1].rstrip("/")

# Create the database if it doesn't exist.
if not os.path.exists("seedbox-sync.sqlite"):
 print("No database found, creating new one...")
 con=sqlite3.connect("seedbox-sync.sqlite")
 con.execute("create table rememberedFiles(filename varchar);")
else:
 con=sqlite3.connect("seedbox-sync.sqlite")

def isFileRemembered(filename):
 cur=con.cursor()
 cur.execute("select count(*) from rememberedFiles where filename=?",(filename,))
 r=[row[0] for row in cur.fetchall()][0]
 cur.close()
 return r>0

def rememberFile(filename):
 con.execute("insert into rememberedFiles values(?)",(filename,))
 con.commit()

# The main loop.
while True:
 files=os.listdir(u""+sourceDir) # If you call os.listdir() with a UTF-8 string the result will be an array of UTF-8 strings instead of ASCII. Needed for passing UTF-8 into sqlite3 for filenames with special characters.
 
 print("Sleeping for 10 seconds...")
 sleep(10) # Sleep for 10 seconds between scans.
 
 for file in files:
  if(isFileRemembered(file)):
   # This file has been copied already.
   print("Skipping file: "+file)
   continue

  # Sync the file.
  print("Syncing new file: "+file)
  cmd=["rsync"]
  #cmd.append("--rsh=ssh -p22222") # Uncomment this line if your target directory or machine is listening on a port other than 22.
  if "--verbose" in sys.argv:
   cmd.append("--verbose")
  if "--progress" in sys.argv:
   cmd.append("--progress")
   
  # Give files in destination 0777 permissions for some NAS setups, but optional.
  cmd.append("--chmod=ugo+rwx")
  cmd.append("--perms")
  
  cmd.append("--delay-updates")
  cmd.append("--recursive")
  cmd.append(sourceDir+"/"+file)
  cmd.append(destDir+"/")
  p=subprocess.Popen(cmd,shell=False)
  if p.wait()==0:
   rememberFile(file)
   print("Synced & remembered: "+file)
  else:
   print("Failed to sync: "+file)

con.close()
