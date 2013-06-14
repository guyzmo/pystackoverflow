#!/usr/bin/env python

import re
import os
import sys
import time
import pprint
import pickle
import requests
import requests.utils
from BeautifulSoup import BeautifulSoup

from stackoverflow.utils import unescape, html2md

class StackOverflowBase:
    def __init__(self, username, password, site, cookies_file=None):
        self.username = username
        self.password = password
        self.site = site
        if cookies_file:
            cookies_file = os.path.expanduser(cookies_file)
        self.cookies_file = cookies_file

    def __enter__(self):
        self.session = requests.Session()
        has_cookies = False
        if self.cookies_file and os.path.exists(self.cookies_file):
            with open(self.cookies_file, 'r') as f:
                d = pickle.load(f)
                cookies = requests.utils.cookiejar_from_dict(d)
                self.session.cookies = cookies
        return self

    def __exit__(self, *args):
        cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
        if '.stackoverflow.com' in self.session.cookies.list_domains():
            cookies = self.session.cookies.get_dict('.stackoverflow.com')
        if self.cookies_file:
            with open(self.cookies_file, 'w') as f:
                pickle.dump(cookies, f)

    def authenticate(self, cookies=False):
        raise NotImplementedError

    def is_authenticated(self):
        r = self.session.head('http://%s/inbox/genuwine' %
                            (self.site,))
        if r.status_code != 404:
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

    def get_questions(self, sort='newest', number='50'):
        r = self.session.get('http://%s/questions' % (self.site,),
                             params={"sort":sort, "pagesize":number})
        ql = BeautifulSoup(r.text).findAll(attrs={'class': 'question-summary'})
        for q in ql:
            yield {
                "id": q['id'].split('-')[-1],
                "url": q.find('h3').find('a', href=True)['href'],
                "title": q.find('h3').text,
                "views": q.find(attrs={'class': 'views '}).text.split(' ')[0],
                "votes": q.find(attrs={'class': 'vote-count-post '}).text,
                "answs": (q.find(attrs={'class': 'status unanswered'}) \
                        or q.find(attrs={'class': 'status answered'})).find('strong').text,
                "summary": q.find(attrs={'class': 'excerpt'}).text,
                "tags": [t.text for t in q.findAll(attrs={'class': 'post-tag'})],
                "user": q.find(attrs={'class': 'user-details'}).find('a').text
            }

    def get_answers(self, question):
        r = self.session.get('http://%s/questions/%s' % (self.site, question))
        q = BeautifulSoup(r.text).find(attrs={'class': 'question'})
        a = BeautifulSoup(r.text).find(attrs={'id': 'answers'})
        qd = {}
        ad = []

        qd['title'] = BeautifulSoup(r.text).find(attrs={'id': 'question-header'}).find('h1').text
        qd['votes'] = q.find(attrs={'class': 'vote-count-post '}).text
        qd['favos'] = q.find(attrs={'class': 'favoritecount'}).text
        qd['text'] = html2md(str(BeautifulSoup(r.text).find(attrs={'class': 'post-text'}).extract()))
        qd['tags'] = [t.text for t in q.findAll(attrs={'class': 'post-tag'})],
        qd['users'] = []
        u = q.find(attrs={'class': 'post-signature owner'})
        for u in u.findAll(attrs={'class': 'user-info '}):
            avatar = u.find(attrs={'class': 'user-gravatar32'}).find('img')
            username = u.find(attrs={'class': 'user-details'}).find('a')
            reputation = u.find(attrs={'class': 'reputation-score'})
            qd['users'].append({
                'owner': True,
                'last_edit': u.find(attrs={'class': 'user-action-time'}).find('span')['title'],
                'avatar': avatar['src'] if avatar else "",
                'username': username.text if username else "",
                'reputation': reputation.text if reputation else ""
            })

        for u in q.findAll(attrs={'class': 'post-signature'}):
            for u in u.findAll(attrs={'class': 'user-info '}):
                avatar = u.find(attrs={'class': 'user-gravatar32'}).find('img')
                username = u.find(attrs={'class': 'user-details'}).find('a')
                reputation = u.find(attrs={'class': 'reputation-score'})
                qd['users'].append({
                    'last_edit': u.find(attrs={'class': 'user-action-time'}).find('span')['title'],
                    'avatar': avatar['src'] if avatar else "",
                    'username': username.text if username else "",
                    'reputation': reputation.text if reputation else ""
                })
        qd['comments'] = []
        for c in q.findAll(attrs={'class': 'comment'}):
            qd['comments'].append({
                'id': c['id'].split('-')[-1],
                'score': c.find(attrs={'class': 'comment-score'}).text,
                'text': c.find(attrs={'class': 'comment-copy'}).text,
                'user': c.find(attrs={'class': 'comment-user'}).text,
                'last_edit': c.find(attrs={'class': 'comment-date'}).find('span')['title'],
            })

        for aa in a.findAll(attrs={'class': re.compile(r'^answer( accepted-answer)?$')}):
            aad = {
                'id': aa['id'].split('-')[-1],
                'accepted': 'accepted-answer' in aa['class'],
                'votes': aa.find(attrs={'class': 'vote-count-post '}).text,
                'text': html2md(str(aa.find(attrs={'class': 'post-text'}))),
                'users': [],
                'comments': []
            }
            for u in aa.findAll(attrs={'class': 'post-signature'}):
                avatar = u.find(attrs={'class': 'user-gravatar32'}).find('img')
                username = u.find(attrs={'class': 'user-details'}).find('a')
                reputation = u.find(attrs={'class': 'reputation-score'})
                aad['users'].append({
                    'last_edit': u.find(attrs={'class': 'user-action-time'}).find('span')['title'],
                    'avatar': avatar['src'] if avatar else "",
                    'username': username.text if username else "",
                    'reputation': reputation.text if reputation else ""
                })

            for c in aa.findAll(attrs={'class': 'comment'}):
                user = c.find(attrs={'class': 'comment-user'})
                aad['comments'].append({
                    'id': c['id'].split('-')[-1],
                    'score': c.find(attrs={'class': 'comment-score'}).text,
                    'text': c.find(attrs={'class': 'comment-copy'}).text,
                    'user': user.text if user else "",
                    'last_edit': c.find(attrs={'class': 'comment-date'}).find('span')['title'],
                })
            ad.append(aad)


        return dict(question=qd, answers=ad)


    def get_inbox(self):
        return self.session.get('http://%s/inbox/genuwine' % (self.site,)).json()


