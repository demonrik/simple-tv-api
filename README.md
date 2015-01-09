simple-tv-api
=============
This is an api for accessing and playing back Simple.tv recordings.

Downloading Recordings
======================

This is an automated python script used to download all recordings from your simple.tv device to your local computer.   Recordings are placed in the parent directory with the name /[Show]/[Season XX]/'show - SXXEYY- [title].mp4'.  
  
This is intended to be run in a hidden folder inside your TV shows directory.   
eg: /home/you/TV Shows/.simple-tv-api/download.py  
If Show and Season folders do not exist the script will make them.   
  
Please set auto-login details in download.py before first run for proper auto-completion.  
  
For regular use, change AUTO_DELETE to True so you don't re-download all recordings everytime script is run.  
Be sure to test downloads are working before turning this on so you don't lose your recordings.

Example usage:

```python download.py```


API Server
==========

Example usage:

```python server.py [username] [password]```

This starts a webserver that can be accessed on port 8080. To get started, access the following url in your browser:

```http://localhost:8080 ```

-> This returns a list of shows recorded on your device.

Make another request using the 'url' parameter of each to access a list of episodes for the given show.

```http://localhost:8080/episodes?group_id=fffffff-ffff-ffff-ffff-ffffffffffff ```

-> This returns a list of episodes for the given show.

Again use the url parameter (notice the common theme here :) ), to download or stream the episode to your computer. For example, paste this url in vlc to watch on your linux machine. No silverlight support required.

```http://localhost:8080/stream?group_id=fffffff-ffff-ffff-ffff-ffffffffffff&instance_id=fffffff-ffff-ffff-ffff-ffffffffffff&item_id=fffffff-ffff-ffff-ffff-ffffffffffff ```

Optionally append ?quality=0 or 1 or 2 to change the quality.

Uses
====

This can be used to assemble an alternative web client for simple tv, download recordings, etc. The possibilities are endless!
