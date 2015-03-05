#-------------------------------------------------------------------------------
# This is an automated python script used to download recordings from your 
# simple.tv device to your local computer. Recordings are placed in the 
# directory specified through the command line or configuration file
# with the name 'episode.mp4', under directories for the show and optionally
# the season.
#-------------------------------------------------------------------------------
import getpass
import api
import urllib
import urllib3
import os
import ConfigParser
import argparse
import platform
import logging
import sys
import unicodedata
import time
from time import strftime

AUTO_DELETE = False

# Some global params to be used - am sure there is a better way to do these....
stv_show_path = u""
stv_sync_list = {}
stv_skip_list = {}
stv_args_list = ['--config','--store','--autodelete','--interactive','--logfile','--loglevel','--quality']
stv_illegal_chars_list_cmn = [':']
stv_illegal_chars_list_win = ['|','/','?','<','>','*','\\','"']
stv_quality = ""

LOGLEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

QUALITYLEVELS = {'auto':'0',
                 'full':'4500000',
                 'high':'2000000',
                 'medium':'1300000',
                 'low':'800000'}

def select_show(stv):
    shows = simple.get_shows()
    for val, show in enumerate(shows):
        # Only display shows with recordings (>0)
        if int(show['recordings']) != 0:
            print str(val) + ": " + show['name'].encode('utf-8') + " [" + show['recordings'] + " episodes]"
            logging.info(str(val) + ": " + show['name'].encode('utf-8') + " [" + show['recordings'] + " episodes]")
    show_id = raw_input("Select show (#): ")
    print "-" * 25
    if show_id.lower() == 'a' or show_id == '':
        print "Download all shows, all episodes"
        download_all_shows(shows,stv)
    else:                # Specific show selected, pass that along to select_episode
        show = shows[int(show_id)]
        select_episode(show)


def select_episode(show):
    # Display list of episodes from show[] to choose form. BYPASSED by download_all_shows()
    group_id = show['group_id']
    episodes = simple.get_episodes(group_id)
    episodes = generate_filename_menu(episodes, show)
    episode_id = raw_input("Select episode (#) or [A]ll Episodes (default): ")

    # Download one (or all) of the episodes with a call to download_episode()
    if episode_id == 'A' or episode_id == 'a' or episode_id == '':
        print "Downloading All files.."
        for x in range(len(episodes)):
            episode = episodes[x]
            download_episode(show, episode, QUALITYLEVELS.get(stv_quality,'4500000'))
    else:
        episode = episodes[int(episode_id)]
        download_episode(show, episode, QUALITYLEVELS.get(stv_quality,'4500000'))


def generate_filename_menu(episodes, show):
    global stv_show_path
    for val, episode in enumerate(episodes):
        # Does not have Series / Episode numbers (probably a movie)
        if episode['season'] == 0:
            #Probably a movie, or special without any season info
            #create a dir for this special and place the file in it.
            logging.warn("No Season Info Found - Must be a Movie, or once off")

            if show['name'] != episode['title']:
                show['name'] = sanitize_filename(show['name'])
                episode['filename'] = "{showname}/{name} - {title}".format(
                    showname=show['name'],
                    name=show['name'],
                    title=sanitize_filename(episode['title']))
            else:
                show['name'] = sanitize_filename(show['name'])
                episode['filename'] = "{showname}/{name}".format(
                    showname=show['name'],
                    name=show['name'])

            showdir = stv_show_path + '{name}/'.format(name=show['name'])
            if not os.path.exists(showdir):
                try:
                    os.makedirs(showdir)
                except OSError:
                    logging.error("Unable to create directory for " + showdir)
                    pass

        else:
            logging.debug("Found Season and Episode info - Processing...")
            show['name'] = sanitize_filename(show['name'])
            episode['season'] = str(episode['season']).zfill(2)         # Pad with leading 0 if < 10
            episode['episode'] = str(episode['episode']).zfill(2)        # Pad with leading 0 if < 10
            showdir = stv_show_path + "{name}/Season {season}/".format(
                name=show['name'],
                season=episode['season']
                )
            try:
                os.makedirs(showdir)
            except OSError:
                pass
            # Display season and episode numbers
            episode['filename'] = u"{name}/Season {season}/{name} - S{season}E{episode} - {title}".format(
                name=show['name'],
                season=episode['season'],
                episode=episode['episode'],
                title=sanitize_filename(episode['title'])
                )
            print str(val) + ": " + episode['filename'].encode("utf-8")
            logging.info(str(val) + ": " + episode['filename'].encode("utf-8"))
    return episodes
    
def sanitize_filename(filename):
    clean_filename = filename
    for n in stv_illegal_chars_list_cmn:
        clean_filename = clean_filename.replace(n,"-")
    if platform.system() == 'Windows':
        for n in stv_illegal_chars_list_win:
            clean_filename = clean_filename.replace(n,"-")
    logging.debug("Cleaning " + filename + " to " + clean_filename)
    return clean_filename
    
def download_episode(show, episode, quality):
    global stv_show_path
    instance_id = episode['instance_id']
    item_id = episode['item_id']
    group_id = show['group_id']
    file_name = stv_show_path + episode['filename'] + '.mp4'

    if not os.path.exists(file_name):

      url = simple.retrieve_episode_mp4(group_id, instance_id, item_id, quality)
      if not url:
          logging.error("Unable to retrieve URL for " \
                + show['name'] + " " \
                + episode['season'] + " " \
                + episode['episode'] + \
                ". Skipping...")
          return
      logging.debug("About to fetch " + file_name + " from: " + url)
      print "Downloading Episode: " + file_name.encode('utf-8')
      logging.info("Downloading Episode: " + file_name)
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
          logging.info("[" + episode['filename'] + "] deleted from Simple.TV")
    else:
      logging.info("File already exists, skipping...")

def is_show_skipped(show, stv):
    if stv_sync_list[stv]['shows2skip']:
        shows2skip = stv_sync_list[stv]['shows2skip'].split(',')
        for shows in shows2skip:
            if show['name'] == shows.replace('"',''):
                return True
    return False

def get_epsiode_quality(urls, prev_quality):
    # Extract the Quality numbers from the urls
    qual_levels = []
    for n in range(0, len(urls)):
        qual_levels.append(urls[n][3:-4])
        logging.debug("Adding Quality Level: " + urls[n][3:-4])
    qual_levels.sort(key=int,reverse=True)

    if QUALITYLEVELS.get(stv_quality,'0') == '0':
        #Auto is being used - going to start at highest quality, if no available
        if int(prev_quality) == 0:
            logging.debug("No previous quality - selecting " + qual_levels[0])
            return qual_levels[0]
        
        #If there was a previous quality used, we should try and go lower
        for lvl in range(0,len(qual_levels)):
            if int(qual_levels[lvl]) < int(prev_quality):
                return qual_levels[lvl]
    else:
        #Quality was requested - do we have it?
        for lvl in range(0,len(qual_levels)):
            if qual_levels[lvl] == QUALITYLEVELS.get(stv_quality,'0'):
                return qual_levels[lvl]
    return '0'

def download_all_shows(shows,stv):
    for val, show in enumerate(shows):
        show = shows[val]
        if is_show_skipped(show, stv): 
            logging.info("Skipping " + show['name'] + ": [ID]-" + show['group_id'])
            continue
        # Only download shows with recordings
        if int(show['recordings']) != 0:
            logging.info("Downloading " + show['name'] + " gid: " + show['group_id'])
            group_id = show['group_id']
            episodes = simple.get_episodes(group_id)
            episodes = generate_filename_menu(episodes, show)
            for x in range(len(episodes)):
                episode = episodes[x]

                # Quick Check to see if the file is already downloaded... can save a few cycles
                file_name = stv_show_path + episode['filename'] + '.mp4'
                if os.path.exists(file_name):
                    logging.info("File Already Exists: " + file_name)
                    continue

                s_info = simple._get_stream_urls(group_id, episode['instance_id'], episode['item_id'])
                quality = get_epsiode_quality(s_info['urls'], '0')
                if quality == '0':
                    logging.error('Couldn\'t find the quality required: ' + stv_quality)
                    continue
                else:
                    logging.info("Selecting Quality: " + quality)
                    download_episode(show, episode, quality)

def auto_download_all(stv):
    print "Auto Download all shows, all episodes"
    shows = simple.get_shows()
    for val, show in enumerate(shows):
        # Only display shows with recordings (>0)
        if int(show['recordings']) != 0:
            logging.info(str(val) + ": " + show['name'].encode('utf-8') + " [" + show['recordings'] + " episodes]")
    download_all_shows(shows,stv)

def parse_config_file(args,config_file):
    global stv_show_path
    global stv_sync_list
    global stv_skip_list
    global logging
    global stv_quality
    
    config = ConfigParser.ConfigParser()
    if args.config: 
        config.read(args.config)
    else:
        config.read(config_file)
    
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
                stv_sync_list[dvr_list[n]]['shows2skip'] = sections[dvr_list[n]]['shows2skip']
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
                    
        if sections['STVAPI']['store']:
            # First lets see if it was passed on the command line
            if args.store:
                stv_show_path = args.store
            else:
                stv_show_path = sections['STVAPI']['store']
            #ensure we have trailing path seperator
            if not stv_show_path.endswith(os.sep):
                stv_show_path+=os.sep
            print "Storing to - " + stv_show_path
                    
        # Extract Logging Information
        loglevel = 'warning'
        if args.loglevel:
            loglevel = args.loglevel
        else:
            if sections['STVAPI']['loglevel']:
                loglevel = sections['STVAPI']['loglevel']


        if args.logfile:
            logfile = args.logfile
            logging.basicConfig(filename=logfile,
                                level=LOGLEVELS.get(loglevel, logging.WARNING))
        else:
            if sections['STVAPI']['logfile']:
                logfile = sections['STVAPI']['logfile']
                logging.basicConfig(filename=logfile,
                                    level=LOGLEVELS.get(loglevel, logging.WARNING))
            else:
                # Need to setup stdout error handler
                logging.basicConfig(stream=sys.stdout,
                                    level=LOGLEVELS.get(loglevel, logging.WARNING))
        
        if (args.quality):
            stv_quality = args.quality
        else:
            if sections['STVAPI']['quality']:
                stv_quality = sections['STVAPI']['quality']
        if stv_quality == "":
            stv_quality = 'auto'

if __name__ == "__main__":
    interactive = False;
    arg_parser = argparse.ArgumentParser(description='Process command line args')
    for n in stv_args_list:
        arg_parser.add_argument(n)
  
    args = arg_parser.parse_args()
    if args.config:
        if os.path.exists(args.config): 
            parse_config_file(args,None)
        else:
            print "Config file specified not found - " + args.config
            interactive = True
    else:
        if os.path.exists('stv-api.ini'):
            parse_config_file(args,'stv-api.ini')
        else:
            print "No config file found - reverting to interactive"
            interactive = True

    # user can always override the settings.            
    if args.interactive:
        interactive = True

    if interactive:
        stv = raw_input("Enter STV Name: ")
        stv_sync_list[stv] = {}
        stv_sync_list[stv]['user'] = raw_input("Enter email: ")
        stv_sync_list[stv]['pass'] = getpass.getpass("Enter password: ")
        stv_sync_list[stv]['shows2skip'] = "" 
        stv_show_path = raw_input("Enter path to store shows: ")
        stv_quality = raw_input("Which quality to get auto, full, high, medium or low: ")
        #ensure we have trailing path seperator
        if not stv_show_path.endswith(os.sep):
            stv_show_path+=os.sep

        loglevel = 'warning'
        if args.loglevel:
            loglevel = args.loglevel
        if args.logfile:
            logfile = args.logfile
            logging.basicConfig(filename=logfile,
                                level=LOGLEVELS.get(loglevel, logging.WARNING))
        else:
            logging.basicConfig(stream=sys.stdout,
                                level=LOGLEVELS.get(loglevel, logging.WARNING))
    else:
        logging.info('==================================================================')
        logging.info(' STV API Download Script - Downloading Today: ' + strftime("%Y-%m-%d %H:%M:%S"))
        logging.info('==================================================================')
        logging.info('Processing the following STVs...')
        for n in stv_sync_list.keys():
            logging.info(n)
            logging.info("Skipping the following shows: \n" + stv_sync_list[n]['shows2skip'])
        for n in stv_skip_list.keys():
            logging.info("Skipping " + n)
        logging.info("Quality set to: " + stv_quality)

    for stv in stv_sync_list.keys():
        logging.info("Logging in to " + stv + "....")
        simple = api.SimpleTV(stv_sync_list[stv]['user'],stv_sync_list[stv]['pass'],stv)
        if interactive:
            select_show(stv);
        else:
            auto_download_all(stv);
        del simple
