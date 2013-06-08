#!/usr/bin/env python

import os
import sys
import time
import pprint
import pickle
import requests
import requests.utils
from BeautifulSoup import BeautifulSoup

from stackoverflow.utils import unescape


class StackOverflowBase:
    def __init__(self, username, password, site, cookies_file=None):
        self.username = username
        self.password = password
        self.site = site
        self.cookies_file = cookies_file

    def __enter__(self):
        self.session = requests.Session()
        has_cookies = False
        if self.cookies_file and os.path.exists(self.cookies_file):
            with open(self.cookies_file, 'r') as f:
                cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
                self.session.cookies = cookies
                has_cookies = True
        self.authenticate(cookies=has_cookies)
        return self

    def __exit__(self, *args):
        if self.cookies_file:
            with open(self.cookies_file, 'w') as f:
                pickle.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)

    def authenticate(self, cookies=False):
        raise NotImplementedError

    def is_authenticated(self):
        if self.session.get('http://%s/inbox/genuwine' %
                            (self.site,)).status_code != 404:
            return True
        # if authentication fails, reset cookies
        cookies = requests.utils.cookiejar_from_dict({})
        self.session.cookies = cookies
        return False


    def connect_to_chat(self, room, cb=lambda e: pprint.PrettyPrinter(indent=4).pprint(e)):
        r = self.session.get('http://chat.%s/rooms/%d/chat-feedback' % (self.site, room))
        if "You must be" in r.text:
            raise Exception("Logging error, can't connect to chat")

        if r.status_code == 404:
            raise Exception("Room #%d not found." % room)

        fkey = BeautifulSoup(r.text).findAll(attrs={'name' : 'fkey'})[0]['value']
        lasttime = 0
        while True:
            payload = {'fkey': fkey,
                    'since': lasttime,
                    'mode': 'Messages' }
            r = self.session.post("http://chat.%s/chats/%d/events" % (self.site, room), data=payload)
            data = r.json()
            for e in data['events']:
                if 'time_stamp' in e and e['time_stamp'] > lasttime:
                    if e['room_id'] == room:
                        if e['event_type'] in (1, 2) and 'content' in e:
                            cb(e)
            lasttime = data['sync']
            time.sleep(2)

    def send_to_chat(self, room, msg):
        r = self.session.get('http://chat.%s/rooms/%d/chat-feedback' % (self.site, room))
        if "You must be" in r.text:
            print "Logging error, can't connect to chat"
            sys.exit(2)

        fkey = BeautifulSoup(r.text).findAll(attrs={'name' : 'fkey'})[0]['value']

        payload = {'fkey': fkey,
                'text': msg}
        self.session.post("http://chat.%s/chats/%d/messages/new" % (self.site, room), data=payload)

    def list_all_rooms(self):
        r = self.session.get('http://chat.%s/rooms' % (self.site,), params={'tab': 'all', 'sort': 'created'})
        rooms = BeautifulSoup(r.text).findAll(attrs={'class': 'roomcard'})
        roomd = {}
        for room in rooms:
            r_id = room.get('id').split('-')[-1]
            name = room.find(attrs={'class': 'room-name'}).text
            users = room.find(attrs={'class': 'room-user-count'}).text
            last = room.find(attrs={'class': 'last-activity'}).text
            msgs = room.find(attrs={'class': 'room-message-count'}).text
            roomd[r_id] = {
                'name': unescape(name),
                'nb_users': unescape(users),
                'last_act': unescape(last),
                'nb_mesgs': unescape(msgs)
            }
        return roomd

    def lookup_question(self, query):
        pass

    def get_questions(self, sort='newest'):
        return self.session.get('http://%s/questions?sort=%s' % (self.site, sort))

    def get_answers(self, question):
        pass

    def get_inbox(self):
        return self.session.get('http://%s/inbox/genuwine' % (self.site,)).json()


