#!/usr/bin/env python

import requests
from BeautifulSoup import BeautifulSoup

from stackoverflow.utils import unescape

class StackExchange:
    def list(self):

        r = requests.get('http://stackexchange.com/sites',
                         params={'view': 'list'})
        l = BeautifulSoup(r.text).findAll(attrs={'class': 'lv-info'})
        for i in l:
            d = dict(name = unescape(i.find('h2').text),
                     url = unescape(i.find('a', href=True)['href']).split('http://')[-1],
                     desc = unescape(i.find(attrs={'class': 'lv-description'}).text))
            yield d

