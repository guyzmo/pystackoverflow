#!/usr/bin/env python

import sys
import urllib
from BeautifulSoup import BeautifulSoup

from stackoverflow.base import StackOverflowBase

class StackOverflow_GoogleAuth(StackOverflowBase):
    def authenticate(self):
        if self.is_authenticated():
            return
        google_accounts_url = 'http://accounts.google.com'
        authentication_url = 'https://accounts.google.com/ServiceLoginAuth'
        stack_overflow_url = 'http://%s/users/authenticate' % (self.site,)

        r = self.session.get(google_accounts_url)
        dsh = BeautifulSoup(r.text).findAll(attrs={'name' : 'dsh'})[0].get('value').encode()
        auto = r.headers['X-Auto-Login']
        follow_up = urllib.unquote(urllib.unquote(auto)).split('continue=')[-1]
        galx = r.cookies['GALX']

        payload = {'continue' : follow_up,
                'followup' : follow_up,
                'dsh' : dsh,
                'GALX' : galx,
                'pstMsg' : 1,
                'dnConn' : 'https://accounts.youtube.com',
                'checkConnection' : '',
                'checkedDomains' : '',
                'timeStmp' : '',
                'secTok' : '',
                'Email' : self.username,
                'Passwd' : self.password,
                'signIn' : 'Sign in',
                'PersistentCookie' : 'yes',
                'rmShown' : 1}

        r = self.session.post(authentication_url, data=payload)

        if r.url == authentication_url:
            raise Exception("Login failed.")

        payload = {'oauth_version' : '',
                'oauth_server' : '',
                'openid_username' : '',
                'openid_identifier' : ''}
        r = self.session.post(stack_overflow_url, data=payload)


