#!/usr/bin/env python

import sys
import time
import pprint
import requests
from BeautifulSoup import BeautifulSoup

from stackoverflow.utils import unescape


class StackOverflowBase:
    def __init__(self, username, password, site):
        self.username = username
        self.password = password
        self.site = site
        self.session = requests.Session()
        self.authenticate()

    def authenticate(self):
        raise NotImplementedError

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

    def get_inbox(self):
        return self.session.get('http://%s/inbox/genuwine' % (self.site,)).json()


