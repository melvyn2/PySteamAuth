
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

from typing import List
import requests
import requests.cookies
import base64
import lxml.html
import json

from Common import error_popup


class Empty:
    pass


class Confirmation(object):
    def __init__(self, conf_id, conf_key, conf_type, conf_creator,
                 conf_description, conf_sub_description, conf_time, conf_icon_url):
        self.id = conf_id
        self.key = conf_key
        self.type = int(conf_type)
        type_switch = {
            1: 'Generic',
            2: 'Trade',
            3: 'Market Listing',
            5: 'Steam Details Change'
        }
        self.type_str = type_switch.get(self.type, 'Unknown')
        self.creator = conf_creator
        self.description = conf_description
        self.sub_description = conf_sub_description
        self.time = conf_time
        self.icon_url = conf_icon_url

    def accept(self, sa):
        return confirm(sa, self, 'allow')

    def deny(self, sa):
        return confirm(sa, self, 'cancel')


def generate_query(tag, sa):
    return {'op': tag, 'p': sa.secrets['device_id'], 'a': sa.secrets['Session']['SteamID'],
            'k': base64.b64encode(sa.get_confirmation_key(tag)).decode('utf-8'), 't': sa.get_time(),
            'm': 'android', 'tag': tag}


def generate_cookiejar(sa):
    jar = requests.cookies.RequestsCookieJar()
    jar.set('mobileClientVersion', '0 (2.1.3)')
    jar.set('mobileClient', 'android')
    jar.set('steamid', str(sa.secrets['Session']['SteamID']))
    jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']))
    jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), secure=True)
    jar.set('Steam_Language', 'english')
    jar.set('sessionid', str(sa.secrets['Session']['SessionID']))
    return jar


def fetch_confirmations(sa):
    conf_url = 'https://steamcommunity.com/mobileconf/conf'
    data = generate_query('conf', sa)
    jar = generate_cookiejar(sa)
    try:
        r = requests.get(conf_url, params="&".join("%s=%s" % (k, v) for k, v in data.items()), cookies=jar)
    except requests.exceptions.ConnectionError:
        error_popup('Connection Error.')
        return []
    # except requests.exceptions.InvalidSchema:
    #     TODO Finish this
    #     pass

    # Used for testing purposes
    # with open('page.html') as f:
    #     r = Empty()
    #     r.text = f.read()

    if '<div>Nothing to confirm</div>' in r.text:
        return []
    ret = []
    # Due to the complexity of lxml, variable annotation was needed to assist pycharm
    doc: lxml.html.HtmlElement = lxml.html.fromstring(r.text)
    # noinspection PyUnusedLocal
    e: lxml.html.HtmlElement
    for e in doc.find_class('mobileconf_list_entry'):
        confid = e.get('data-confid')
        key = e.get('data-key')
        conftype = e.get('data-type')
        creator = e.get('data-creator')
        try:
            icon_url = e.find_class('playerAvatar')[0].find('img').get('src').replace('.jpg', '_full.jpg')
        except IndexError:
            icon_url = False
        # desc_block[0] is the confirmation title, [1] is the sub-description, and [2] is the time of the confirmation
        desc_block: List[lxml.html.HtmlElement] = e.find_class('mobileconf_list_entry_description')[0].findall('div')
        ret.append(Confirmation(confid, key, conftype, creator, desc_block[0].text_content(),
                                desc_block[1].text_content(), desc_block[2].text_content(), icon_url))
    return ret


def confirm(sa, conf, action):
    url = 'https://steamcommunity.com/mobileconf/ajaxop'
    data = generate_query(action, sa)
    data.update({'cid': conf.id, 'ck': conf.key})
    jar = generate_cookiejar(sa)
    try:
        r = requests.get(url, params="&".join("%s=%s" % (k, v) for k, v in data.items()), cookies=jar)
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
        error_popup('Connection error.')
        return False
    if json.loads(r.text)["success"]:
        return True
    else:
        return False


def confirm_multi(sa, confs, action):
    url = 'https://steamcommunity.com/mobileconf/multiajaxop'
    data = generate_query(action, sa)
    for i in confs:
        data.update({'cid[]': i.id, 'ck[]': i.key})
    jar = generate_cookiejar(sa)
    try:
        r = requests.post(url, data=data, cookies=jar)
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
        error_popup('Connection error.')
        return False
    if json.loads(r.text)["success"]:
        return True
    else:
        error_popup('Confirmation error.')
        return False
