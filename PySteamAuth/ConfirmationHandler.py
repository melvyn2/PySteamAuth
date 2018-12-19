
#    Copyright (c) 2018 melvyn2
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

import requests
import requests.cookies
import urllib.parse
import binascii
import re
import json
try:
    from . import AccountHandler
except ImportError:
    # noinspection PyUnresolvedReferences
    import AccountHandler


class Empty:
    pass


class Confirmation(object):
    def __init__(self, conf_id, conf_key, conf_type, conf_creator,
                 conf_description, conf_sub_description, conf_time, conf_icon_url):
        self.id = conf_id
        self.key = conf_key
        self.type = conf_type
        type_switch = {
            '1': 'Generic',
            '2': 'Trade',
            '3': 'Market Listing'
        }
        self.type_str = type_switch.get(self.type, 'Unknown')
        self.creator = conf_creator
        self.description = conf_description
        self.sub_description = conf_sub_description
        self.time = conf_time
        self.icon_url = conf_icon_url

    def accept(self, sa, main_window, mafiles_path, manifest):
            return confirm(sa, [self], 'allow', main_window, mafiles_path, manifest)

    def deny(self, sa, main_window, mafiles_path, manifest):
            return confirm(sa, [self], 'cancel', main_window, mafiles_path, manifest)


def generate_query(tag, sa):
    return 'p={0}&a={1}&k={2}&t={3}&m=android&tag={4}'\
        .format(sa.secrets['device_id'], sa.secrets['Session']['SteamID'],
                urllib.parse.quote_plus(binascii.b2a_base64(sa.get_confirmation_key(tag))), sa.get_time(), tag)


def fetch_confirmations(sa, main_window, mafiles_path, manifest):
    conf_url = 'https://steamcommunity.com/mobileconf/conf?' + generate_query('conf', sa)
    jar = requests.cookies.RequestsCookieJar()
    jar.set('mobileClientVersion', '0 (2.1.3)', path='/', domain='.steamcommunity.com')
    jar.set('mobileClient', 'android', path='/', domain='.steamcommunity.com')
    jar.set('steamid', str(sa.secrets['Session']['SteamID']), path='/', domain='.steamcommunity.com')
    jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']), path='/', domain='.steamcommunity.com')
    jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), path='/', domain='.steamcommunity.com')
    jar.set('Steam_Language', 'english', path='/', domain='.steamcommunity.com')
    jar.set('sessionid', str(sa.secrets['Session']['SessionID']), path='/', domain='.steamcommunity.com')
    try:
        r = requests.get(conf_url, cookies=jar)
    except requests.exceptions.ConnectionError:
        main_window.error_popup_event.emit('Connection Error.', '')
        return []
    page = ''.join(r.text.replace('\t', '').splitlines())
    # with open('page.html') as f:
    #     r = Empty()
    #     r.text = f.read()
    #     print(r.text)
    conf_full_regex = '<div class="mobileconf_list_entry"((.|\n)*?)' + \
                      '<div class="mobileconf_list_entry_sep"></div>'
    if '<div>Nothing to confirm</div>' in page:
        return []
    ret = []

    for i in [x[0] for x in re.findall(conf_full_regex, page)]:
        try:
            icon_url = re.findall('<img src="(.*?)"', i)[0].replace('.jpg', '_medium.jpg')
        except IndexError:
            icon_url = False
        baseinfo = re.findall('id="conf[0-9]+" data-confid="(\\d+)" ' +
                              'data-key="(\\d+)" data-type="(\\d+)" data-creator="(\\d+)"', i)[0]
        moreinfo = re.findall('<div class="mobileconf_list_entry_description"><div>(.*?)</div>' +
                              '<div>(.*?)</div><div>(.*?)</div>', i)[0]
        ret.append(Confirmation(baseinfo[0],
                                baseinfo[1],
                                baseinfo[2],
                                baseinfo[3],
                                re.sub('<[^>]+>', '', moreinfo[0]),
                                moreinfo[1],
                                moreinfo[2],
                                icon_url))
    return ret


def confirm(sa, confs, action, main_window, mafiles_path, manifest):
    data = 'op=' + action + '&' + generate_query(action, sa)
    print(confs)
    if len(confs) == 0:
        return
    jar = requests.cookies.RequestsCookieJar()
    jar.set('mobileClientVersion', '0 (2.1.3)', path='/', domain='.steamcommunity.com')
    jar.set('mobileClient', 'android', path='/', domain='.steamcommunity.com')
    jar.set('steamid', str(sa.secrets['Session']['SteamID']), path='/', domain='.steamcommunity.com')
    jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']), path='/', domain='.steamcommunity.com')
    jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), path='/', domain='.steamcommunity.com')
    jar.set('Steam_Language', 'english', path='/', domain='.steamcommunity.com')
    jar.set('sessionid', str(sa.secrets['Session']['SessionID']), path='/', domain='.steamcommunity.com')
    if len(confs) == 1:
        url = 'https://steamcommunity.com/mobileconf/ajaxop?'
        data += '&cid=' + confs[0].id + '&ck=' + confs[0].key
        try:
            if json.loads(requests.get(url + data, cookies=jar).text)["success"]:
                return True
            else:
                return False
        except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
            main_window.error_popup_event.emit('Connection error.', '')
    else:
        url = 'https://steamcommunity.com/mobileconf/multiajaxop'
        for i in confs:
            data += '&cid[]=' + i.id + '&ck[]=' + i.key
        try:
            r = requests.post(url, data=data, cookies=jar)
            if json.loads(r.text)["success"]:
                return True
            else:
                print(url, data, r.text)
                return False
        except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
            main_window.error_popup_event.emit('Connection error.', '')
