#-------------------------------------------------------------------------------
# This file provides a simple API for scraping the web interface to Simple TV
# facilitating extraction of show info, episode lists, finding the MP4 file,
# etc.
#-------------------------------------------------------------------------------
from xml.etree import ElementTree as et
from BeautifulSoup import BeautifulSoup
import requests
import json
import re
import time
import datetime
import logging


class SimpleTV:
    def unescape_html(self, s):
        s = s.replace("&quot;",'"')
        s = s.replace("&apos;","'")
        s = s.replace("&lt;","<")
        s = s.replace("&gt;",">")
        # this has to be last
        s = s.replace("&amp;","&")
        return s

    def __init__(self, username, password, dvr):
        self.remote = None
        clock = datetime.datetime.now()
        self.date = str(clock.year) + \
                    "%2F" + str(clock.month) + \
                    "%2F" + str(clock.day) + \
                    "+" + str(clock.hour) + \
                    "%3A" + str(clock.minute) + \
                    "%3A" + str(clock.second)
        self.utcoffset = (time.timezone / 60)
        self.s = requests.Session()
        self._login(username, password, dvr)

    def _login(self, username, password, dvr):
        url = 'https://us.simple.tv/Auth/SignIn'
        data = {
            'UserName': username,
            'Password': password,
            'RememberMe': 'true'
            }
        r = self.s.post(url, params=data)
        resp = json.loads(r.text)
        if 'SignInError' in resp:
            logging.error("Error logging in")
            raise('Invalid login information')
        # self.sid = resp['MediaServerID']
        r = self.s.get('https://us-my.simple.tv/')
        soup = BeautifulSoup(r.text)
        info = soup.find('section', {'id': 'watchShow'})
        self.account_id = info['data-accountid']
       
        # Get list of DVRs, compare against selected, default to first if
        # none found, or none provided 
        dvr_list, dvr_id_list = self.get_dvr_list(soup)
        self.sid = self.media_server_id = info['data-mediaserverid']
        if dvr_list:
            #find the dvr_unit selected
            dvr_found = False
            for x in range(0,len(dvr_list)):
                if dvr_list[x].text == dvr:
                    self.sid = self.media_server_id = dvr_id_list[x]['data-value']
                    logging.info("Selecting DVR with DeviceID: " + self.sid)
                    dvr_found=True
            if not dvr_found:
                logging.warn("Can't find selected DVR, falling back to DeviceID " + self.sid)
                self.sid = self.media_server_id = info['data-mediaserverid']

        #set the mediserver ID to correct STV
        self.set_dvr()
 
        #Retrieve streaming urls
        r = self.s.get("https://us-my.simple.tv/Data/RealTimeData"
                       "?accountId={}&mediaServerId={}"
                       "&playerAlternativeAvailable=false".format(self.account_id, self.media_server_id))
        resp = json.loads(r.text)
        self.local_base = resp['LocalStreamBaseURL']
        self.remote_base = resp['RemoteStreamBaseURL']
        return True

    def get_dvr_list(self, page):
        dvr_list = []
        dvr_id_list = []
        
        uls = page.findAll('ul',{'class':'switch-dvr-list'})
        if uls:
            for ul in uls:
                for dvrli in ul.findAll('li'):
                    dvr_list.append(dvrli)
                    for dvr_id in dvrli.findAll('a'):
                        dvr_id_list.append(dvr_id)

        for x in range(0, len(dvr_list)):
            logging.debug("Found: " + dvr_list[x].text.encode("utf-8") + "| DeviceID: " + dvr_id_list[x]['data-value'])
        
        return (dvr_list, dvr_id_list)

    def set_dvr(self):
        #set the mediaserver
        url="https://us-my.simple.tv/Account/MediaServers"
        data = {
            'defaultMediaServerID': self.sid
            }
        r = self.s.post(url, params=data)
        return

    def get_shows(self):
        url = 'https://us-my.simple.tv/Library/MyShows'
        url += '?browserDateTimeUTC=' + self.date
        url += '&mediaServerID=' + self.sid
        url += '&browserUTCOffsetMinutes=-300'
        r = self.s.get(url)
        root = et.fromstring(r.text)
        shows = []
        for show in root:
            data = {}
            div = show.find('div')
            info = show.find('figcaption')
            data['group_id'] = show.attrib['data-groupid']
            data['image'] = div.find('img').attrib['src']
            data['name'] = self.unescape_html(info.find('b').text)
            data['recordings'] = info.find('span').text
            shows.append(data)
        return shows

    def get_episodes(self, group_id):
        logging.debug("Finding Episodes for gid: " + group_id)
        url = 'https://us-my.simple.tv/Library/ShowDetail'
        url += '?browserDateTimeUTC=' + self.date
        url += '&browserUTCOffsetMinutes=-300'
        url += '&groupID=' + group_id

        r = self.s.get(url)
        soup = BeautifulSoup(r.text)
        e = soup.find('div', {'id': 'recorded'}).findAll('article')
        episodes = []
        for episode in e:
            data = {}
            # Skip failed episodes for now
            try:
                epiList = episode.findAll('b')
                if len(epiList) == 3:   # Figure out if it's a Show or a Movie
                    data['season'] = int(epiList[1].text)
                    data['episode'] = int(epiList[2].text)
                else:
                    data['season'] = 0
                    data['episode'] = 0
                data['channel'] = str(epiList[0].text)
                links = episode.find('a', {'class': 'button-standard-watch'})
                data['item_id'] = links['data-itemid']
                data['instance_id'] = links['data-instanceid']
                data['title'] = self.unescape_html(episode.h3.find(
                    text=True,
                    recursive=False
                    ).rstrip())
            except:
                continue
            episodes.append(data)
        return episodes

    def _get_stream_urls(self, group_id, instance_id, item_id):
        url = 'https://us-my.simple.tv/Library/Player'
        url += '?browserUTCOffsetMinutes=-300'
        url += '&groupID=' + group_id
        url += '&instanceID=' + instance_id
        url += '&itemID=' + item_id
        url += '&isReachedLocally=' + ("False" if self.remote else "True")
        logging.debug("Fetching stream URLs from: " + url)
        r = self.s.get(url)
        soup = BeautifulSoup(r.text)
        s = soup.find('div', {'id': 'video-player-large'})
        if self.remote:
            logging.debug("STV is remote - settings base: " + self.remote_base)
            base = self.remote_base
        else:
            logging.debug("STV is local - settings base: " + self.local_base)
            base = self.local_base
        req_url = base + s['data-streamlocation'] + ".refcount"
        stream_base = "/".join(req_url.split('/')[:-1]) + "/"

        logging.debug("Fetching streaminfo: " + req_url)

        if self.remote is None:
            try:
                r = self.s.get(req_url, timeout=5)
                self.remote = False
            except:
                self.remote = True
                return self._get_stream_urls(group_id, instance_id, item_id)
        r = self.s.get(req_url)
        logging.debug(r)
        urls = []
        for url in r.text.split('\n'):
            logging.debug("Examining: " + url)
            if (len(url)> 0) and (url[-4] == "."):
                urls.append(url[1:])
                logging.debug("Saving URL: " + url[1:])
        return {'base': stream_base, 'urls': urls}

        
    def retrieve_episode_mp4(self, group_id, instance_id, item_id, quality):
        '''Specify quality using int for entry into m3u8. Typically:
        0 = 500000, 1 = 1500000, 2 = 4500000
        '''
        s_info = self._get_stream_urls(group_id, instance_id, item_id)
        if not s_info['urls']:
            return
        url = s_info['base'] + s_info['urls'][int(quality)]
        logging.debug("Fetching from: " + url)
        return url
