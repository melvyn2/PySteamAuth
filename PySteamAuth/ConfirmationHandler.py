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

import base64
import json
import re

import steam.guard
from typing import List

import requests
import requests.cookies

import Common


class Empty:
    pass


class Confirmation(object):
    def __init__(self, conf_id: int, conf_key: int, conf_type: int, conf_creator: int, conf_icon_url: str,
                 conf_description: str, conf_sub_description: str, conf_time: int):
        self.id = conf_id
        self.key = conf_key
        self.type = conf_type
        type_switch = {
            1: 'Generic',
            2: 'Trade',
            3: 'Market Listing',
            5: 'Steam Details Change'
        }
        self.icon_url = conf_icon_url
        self.type_str = type_switch.get(self.type, 'Unknown')
        self.creator = conf_creator
        self.description = conf_description
        self.sub_description = conf_sub_description
        self.time = conf_time

    def accept(self, sa: steam.guard.SteamAuthenticator):
        return confirm(sa, self, 'allow')

    def deny(self, sa: steam.guard.SteamAuthenticator):
        return confirm(sa, self, 'cancel')


def generate_query(sa: steam.guard.SteamAuthenticator, tag: str):
    return {'op': tag, 'p': sa.secrets['device_id'], 'a': sa.secrets['Session']['SteamID'],
            'k': base64.b64encode(sa.get_confirmation_key(tag)).decode('utf-8'), 't': sa.get_time(),
            'm': 'android', 'tag': tag}


def generate_cookiejar(sa: steam.guard.SteamAuthenticator):
    jar = requests.cookies.RequestsCookieJar()
    jar.set('mobileClientVersion', '0 (2.1.3)')
    jar.set('mobileClient', 'android')
    jar.set('steamid', str(sa.secrets['Session']['SteamID']))
    jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']))
    jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), secure=True)
    jar.set('Steam_Language', 'english')
    jar.set('sessionid', str(sa.secrets['Session']['SessionID']))
    return jar


def fetch_confirmations(sa: steam.guard.SteamAuthenticator):
    url = 'https://steamcommunity.com/mobileconf/conf'
    data = generate_query(sa, 'conf')
    try:
        r = sa.backend.session.get(url, params="&".join("%s=%s" % (k, v) for k, v in data.items()))
    except requests.exceptions.ConnectionError:
        Common.error_popup('Connection Error.')
        return []
    # except requests.exceptions.InvalidSchema:
    #     TODO Finish this, implement project wide
    #     pass

    # Used for testing purposes
    # with open('page.html') as f:
    #     r = Empty()
    #     r.text = f.read()

    if '<div>Nothing to confirm</div>' in r.text:
        return []
    ret = []
    # noinspection PyPep8
    pattern = r'<div class=\"mobileconf_list_entry\" id=\"conf[0-9]+\" data-confid=\"(\d+)\" data-key=\"(\d+)\" ' \
              r'data-type=\"(\d)\" data-creator=\"(\d+)\" data-cancel=\"[a-zA-Z]+\" data-accept=\"[a-zA-Z]+\" >' \
              r'[\s]*?<div class=\"mobileconf_list_entry_content\">[\s]*?<div class=\"mobileconf_list_entry_icon\">' \
              r'[\s]*?(?:<div class=\"[a-zA-Z ]+\"><img src=\"(.*?)\" srcset=\".*? 1x, .*? 2x\"></div>)?[\s]*?</div>' \
              r'[\s]*?<div class=\"mobileconf_list_entry_description\">[\s]*?<div>(.*?)</div>[\s]*?<div>(.*?)</div>' \
              r'[\s]*?<div>(.*?)</div>[\s]*?</div>[\s]*?</div>'
    for i in re.findall(pattern, r.text):
        ret.append(Confirmation(i[0], i[1], i[2], i[3], i[4].replace('.jpg', '_full.jpg'), re.sub('<[^<]+?>', '', i[5]),
                                i[6], i[7]))
    return ret


def confirm(sa: steam.guard.SteamAuthenticator, conf: Confirmation, action: str):
    url = 'https://steamcommunity.com/mobileconf/ajaxop'
    data = generate_query(sa, action)
    data.update({'cid': conf.id, 'ck': conf.key})
    try:
        r = sa.backend.session.get(url, params="&".join("%s=%s" % (k, v) for k, v in data.items()))
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
        Common.error_popup('Connection error.')
        return False
    if json.loads(r.text)["success"]:
        return True
    else:
        return False


def confirm_multi(sa: steam.guard.SteamAuthenticator, confs: List[Confirmation], action: str):
    url = 'https://steamcommunity.com/mobileconf/multiajaxop'
    data = generate_query(sa, action)
    for i in confs:
        data.update({'cid[]': i.id, 'ck[]': i.key})
    try:
        r = sa.backend.requests.post(url, data=data)
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
        Common.error_popup('Connection error.')
        return False
    if json.loads(r.text)["success"]:
        return True
    else:
        Common.error_popup('Confirmation error.')
        return False
