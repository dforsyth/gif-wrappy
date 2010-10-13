#!/usr/bin/env python

# See LICENSE file for license information

import gwcommands

gw_name = 'gif-wrappy'
gw_version = '0.5a'
gw_codename = 'R.I.P. Google Wave.'

hello_message = '\n%s\n%s\n%s' % (gw_name, gw_version, gw_codename)

image_url = None
profile_url = None

blacklist = ['image', 'hosts', 'you', 'dont', 'want', 'to', 'allow']

notag = ['words', 'you', 'think', 'are', 'naughty']

wconfig = { 'admin_pw': 'password',
            'blacklist': blacklist,
            'notag': notag,
            'image_re': r'>>(.*?)\.',
            'command_re': r'::(.*?)::',
            'enforce_bans': False }
