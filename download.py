import getpass
import api
import urllib
import urllib3
import os
import ConfigParser

AUTO_DELETE = False

stv_sync_list = {}
stv_skip_list = {}
user_list = {}


def select_show():
    shows = simple.get_shows()
    for val, show in enumerate(shows):
        # Only display shows with recordings (>0)
        if int(show['recordings']) != 0:
            print str(val) + ": " + show['name'].encode('utf-8') + " [" + show['recordings'] + " episodes]"
    show_id = ''#raw_input("Select show (#): ")
    print "-" * 25
    if show_id.lower() == 'a' or show_id == '':
        print "Download all shows, all episodes"
        download_all_shows(shows)
    else:                # Specific show selected, pass that along to select_episode
        show = shows[int(show_id)]
        select_episode(show)


def select_episode(show):
    """
    Display list of episodes from show[] to choose form. BYPASSED by download_all_shows()
    """
    group_id = show['group_id']
    episodes = simple.get_episodes(group_id)
    episodes = generate_filename_menu(episodes, show)
    episode_id = raw_input("Select episode (#) or [A]ll Episodes (default): ")

    # Download one (or all) of the episodes with a call to download_episode()
    if episode_id == 'A' or episode_id == 'a' or episode_id == '':
        print "Downloading All files.."
        for x in range(len(episodes)):
            episode = episodes[x]
            download_episode(show, episode)
    else:
        episode = episodes[int(episode_id)]
        download_episode(show, episode)


def generate_filename_menu(episodes, show):
    for val, episode in enumerate(episodes):
        # Does not have Series / Episode numbers (probably a movie)
        if episode['season'] == 0:
            if show['name'] != episode['title']:
                episode['filename'] = show['name'] + " - " + episode['title'].encode('utf-8')
            else:
                episode['filename'] = show['name']
        else:
            episode['season'] = str(episode['season']).zfill(2)         # Pad with leading 0 if < 10
            showdir = "../{name}/Season {season}/".format(
                name=show['name'],
                season=episode['season']
                )
            try:
                os.makedirs(showdir)
            except OSError:
                pass
             # Display season and episode numbers
            episode['season'] = str(episode['season']).zfill(2)         # Pad with leading 0 if < 10
            episode['episode'] = str(episode['episode']).zfill(2)        # Pad with leading 0 if < 10
            episode['filename'] = "../{name}/Season {season}/{name} - S{season}E{episode} - {title}".format(
                name=show['name'],
                season=episode['season'],
                episode=episode['episode'],
                title=episode['title']
                )
            episode['filename'] = episode['filename'].replace(":", "-")
            episode['filename'] = episode['filename'].replace("'", "")
            print str(val) + ": " + episode['filename'].encode('utf-8')
    return episodes
    
    
def download_episode(show, episode):
    instance_id = episode['instance_id']
    item_id = episode['item_id']
    quality = 0
    group_id = show['group_id']
    file_name = episode['filename'] + '.mp4'

    if not os.path.exists(file_name):
      url = simple.retrieve_episode_mp4(group_id, instance_id, item_id, quality)
      if not url:
          print "Unable to retrieve URL for " \
                + show['name'] + " " \
                + episode['season'] + " " \
                + episode['episode'] + \
                ". Skipping..."
          return
      print "Downloading " + file_name
      (filename, headers) = urllib.urlretrieve(url, file_name)
      file_size = os.path.getsize(file_name) >> 20
      print "File size: ", file_size , "MB"
      download_complete_bool = True if file_size > 20 else False
      print "download_complete_bool: " , download_complete_bool
      if AUTO_DELETE and download_complete_bool:
          url = "https://stv-p-api1-prod.rsslabs.net/content/actionjson/mediaserver/"
          url += simple.sid
          url += "/instance/"
          url += instance_id
          url += "?filetype=all"
          http = urllib3.PoolManager()
          headers = urllib3.util.make_headers(basic_auth=username + ":" + password)
          http.request('DELETE', url, headers=headers)  # Gives a SSL Cert error. Not sure why..? Need to add 'assert_hostnam$
          print "[" + episode['filename'] + "] deleted from Simple.TV"
    else:
      print "File already exists, skipping..."


def download_all_shows(shows):
    for val, show in enumerate(shows):
        show = shows[val]
        # Only download shows with recordings
        if int(show['recordings']) != 0:
            print "\nDownloading " + show['name']
            group_id = show['group_id']
            episodes = simple.get_episodes(group_id)
            episodes = generate_filename_menu(episodes, show)
            for x in range(len(episodes)):
                episode = episodes[x]
                download_episode(show, episode)

def parse_config_file(configFile):
    config = ConfigParser.ConfigParser()
    config.read(configFile)
    
    sections = {}

    # Parse out the config info from the config file
    for section_name in config.sections():
    	  sections[section_name] = {}
    	  for name, value in config.items(section_name):
    	  	  sections[section_name][name] = value

    # Process the parent section - which DVRs to SYNC or SKIP    
    if 'STVAPI' in sections.keys():

    	  #Build up info on each STV to process
    	  dvr_list = sections['STVAPI']['dvr2sync'].split(',')
    	  for n in range(0,len(dvr_list)):
    	      if dvr_list[n] in sections.keys():
    	          stv_sync_list[dvr_list[n]] = {}
    	          if sections[dvr_list[n]]['dvrlogin'] in sections.keys():
    	          	  stv_sync_list[dvr_list[n]]['user'] = sections[sections[dvr_list[n]]['dvrlogin']]['username']
    	          	  stv_sync_list[dvr_list[n]]['pass'] = sections[sections[dvr_list[n]]['dvrlogin']]['password']

    	  #Do the same for the DVRs to skip
    	  dvr_list = sections['STVAPI']['dvr2skip'].split(',')
    	  for n in range(0,len(dvr_list)):
    	      if dvr_list[n] in sections.keys():
    	          stv_skip_list[dvr_list[n]] = {}
    	          if sections[dvr_list[n]]['dvrlogin'] in sections.keys():
    	          	  stv_skip_list[dvr_list[n]]['user'] = sections[sections[dvr_list[n]]['dvrlogin']]['username']
    	          	  stv_skip_list[dvr_list[n]]['pass'] = sections[sections[dvr_list[n]]['dvrlogin']]['password']
    	          	  
    print 'Processing the following STVs'
    for n in stv_sync_list.keys():
        print n + ":" + stv_sync_list[n]['user'] + ":" + stv_sync_list[n]['pass']
    	
    print 'Skipping the following STVs'
    for n in stv_skip_list.keys():
        print n + ":" + stv_skip_list[n]['user'] + ":" + stv_skip_list[n]['pass']


if __name__ == "__main__":
    parse_config_file('stv-api.ini')

    # Loop through each DVR to process
    for stv in stv_sync_list.keys():
    	  print "Logging in to " + stv + "...."
    	  simple = api.SimpleTV(stv_sync_list[stv]['user'],stv_sync_list[stv]['pass'],stv)
    	  select_show();
    	  del simple
    	  
