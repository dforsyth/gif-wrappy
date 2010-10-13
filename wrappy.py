#/usr/bin/env python

# See LICENSE file for license information

import logging
import random
import re

import gwconfig
from models import Image
from models import Banned

from waveapi import element
from waveapi import events
from waveapi import robot
from waveapi import appengine_robot_runner

#TODO(dforsyth): Add the rest of the command functionality
#TODO(dforsyth): Fix the range issues

def DEBUG(msg):
    logging.debug('debug: %s' % msg)


class WrappyBot(robot.Robot):
    """The control center for the wrappy robot"""

    def __init__(self, _config):
        self._config = _config
        self.wrapper = Wrapper(self._config.wconfig)
        robot.Robot.__init__(self,
            self._config.gw_name,
            image_url=self._config.image_url,
            profile_url=self._config.profile_url)
        
        self.register_handler(events.DocumentChanged, self.on_changed)
        self.register_handler(events.BlipSubmitted, self.on_submitted)
        self.register_handler(events.WaveletSelfAdded, self.on_self_added)

    def on_changed(self, event, wavelet):
        blip = event.blip
        self.wrapper.image_wrap(blip)

    def on_submitted(self, event, wavelet):
        blip = event.blip
        self.wrapper.command_wrap(blip)

    def on_self_added(self, event, wavelet):
        self.write_to_wavelet(wavelet, self._config.hello_message)

    def write_to_wavelet(self, wavelet, message):
        wavelet.reply('%s\n' % message)


class Wrapper(object):
    
    def __init__(self, wconfig):
        self.image_re = re.compile(wconfig['image_re'])
        self.command_re = re.compile(wconfig['command_re'])
        self.blacklist = wconfig['blacklist']
        self.admin_pw = wconfig['admin_pw']
        self.enforce_bans = wconfig['enforce_bans']
        self.notag = wconfig['notag']
        # This is gross but whatever...
        self.commands = {   'add': self._add_image,
                            'list': self._list_tags,
                            'random': self._random_image,
                            'ban' : self._ban_user,
                            'metrics': self._metrics,
                            'rmtag': self._rmtag,
                            'boom' : self._boom,
                            'epeen': self._metrics,
                            'oneshot': self._one_shot}
    
    def image_wrap(self, blip):
        self._wrap(blip, command=False)

    def command_wrap(self, blip):
        self._wrap(blip, command=True)

    def _wrap(self, blip, command=False):
        if not blip:
            pass
        if self.enforce_bans:
            # Blips have no contributors until something has been typed by a
            # person into the blip.
            bans = Banned.all()
            for contributer in blip.contributors:
                bans.filter('name =', contributer)
            if bans.fetch(1):
                return
        results = self.parse_text(blip.text, self.command_re if command else self.image_re)
        self.replace_in_blip(blip, results, command=command)

    def parse_text(self, text, trigger_re):
        """Return a list of three-tuples with (start, end, tags)"""
        DEBUG('parsing: %s' % text)
        ranged_match_list = []
        for match in trigger_re.finditer(text):
            # Take groups()[0] instead of groups(0) so we can get right to the
            # string we want
            tags_str = match.groups()[0]
            DEBUG('match: %s' % tags_str)
            tags_list = [tag.strip() for tag in tags_str.split(',')]
            ranged_match_list.append((match.start() + 1, match.end() - 1, tags_list))
        DEBUG('parse_text: %s' % ranged_match_list)
        return ranged_match_list

    def get_images_by_tags(self, tags):
        """Returns the url of an image in the index that has tags"""
        DEBUG('get_images_by_tags: %s' % tags)
        ltags = [tag.lower() for tag in tags]
        q = Image.all()
        for tag in ltags:
            q.filter('tags =', tag)
        return q.fetch(100)

    def put_image(self, submitter, url, tags):
        DEBUG('put_image: %s (%s)' % (url, tags))
        exists = self.get_image_by_url(url)
        ltags = [tag.lower() for tag in tags]
        if exists:
            DEBUG('found existing %s' % img)
            for image in exists:
                image.tags.extend([tag for tag in ltags if tag not in image.tags])
                image.put()
        else:
            image = Image(url=url, tags=ltags, submitter=submitter)
            image.put()

    def get_image_by_url(self, url):
        DEBUG('get_image_by_url: %s' % url)
        q = Image.all()
        q.filter('url =', url)
        return q.fetch(1)
    
    def _add_image(self, blip, startend, arguments):
        DEBUG('_add_image: %s by %s' % (arguments, blip.creator))
        url = arguments[0]

        # Do some checks to make sure we're alright with what's being added to
        # the database.
        for blacklisted in self.blacklist:
            if url.find(blacklisted) >= 0:
                return
        tags = arguments[1:]
        if len(tags) < 1:
            return
        for no in self.notag:
            if no in tags:
                return

        self.put_image(blip.creator, url, tags)
        self._annotate_range(blip, startend[0] + 1, startend[1], 'style/color',
            'rgb(0, 255, 0)')
    
    def _rmtag(self, blip, startend, arguments):
        url = arguments[0]
        tags = arguments[1:]
        q = Image.all()
        q.filter('url =', url)
        images = q.fetch(1)
        for image in images:
            image.tags = [tag for tag in image.tags if tag not in tags]
            image.put()

    def _random_image(self, blip, startend, argments):
        q = Image.all()
        images = q.fetch(2000)
        i = images[random.randint(0, len(images) - 1)]
        range = blip.range(startend[0], startend[1])
        range.replace(element.Image(url=i.url, caption=str(i.tags)))

    def _list_tags(self, blip, startend, arguments):
        q = Image.all()
        images = q.fetch(2000)
        tag_list = []
        for image in images:
            tag_list.extend(image.tags)
        tag_set = set(tag_list)
        range = blip.range(startend[0], startend[1])
        range.replace(', '.join(tag_set))

    def _ban_user(self, blip, startend, arguments):
        password = arguments[0]
        if password == self.admin_pw:
            for user in arguments[1:]:
                b = Banned(name=user)
                b.put()

    def _metrics(self, blip, startend, arguments):
        q = Image.all()
        images = q.fetch(2000) # fetch needs a 'limit'
        user_dict = {}
        tag_list = []
        image_total = len(images)
        for image in images:
            tag_list.extend(image.tags)
            if image.submitter not in user_dict:
                user_dict[image.submitter] = 1
            else:
                user_dict[image.submitter] = user_dict[image.submitter] + 1
        
        metrics_message = '\n%d images in the database (%d unique tags):\n' % (image_total, len(set(tag_list)))
        for user, count in user_dict.iteritems():
            metrics_message = '%s\n%s: %d (%f%%)' % (metrics_message, user, count, (float(count * 100) / image_total))

        range = blip.range(startend[0], startend[1])
        range.replace(metrics_message)

    def _boom(self, blip, startend, arguments):
        q = Image.all()
        images = q.fetch(2000)
        for image in images:
                blip.append(element.Image(url=image.url, caption=str(image.tags)))

    def _one_shot(self, blip, startend, arguments):
        start, end = startend
        range = blip.range(start, end)
        # Remove the command from the blip
        range.delete()
        for url in arguments:
            blip.append(element.Image(url=image.url, caption=str(url))

    def replace_in_blip(self, blip, ranged_match_list, command=False):
        if not command:
            for start, end, tags in ranged_match_list:
                images = self.get_images_by_tags(tags)
                DEBUG('got images: %s' % images)
                if images:
                    i = images[random.randint(0, len(images) - 1)]
                    range = blip.range(start - 1, end + 1)
                    range.replace(element.Image(url=i.url, caption=str(i.tags)))
                else:
                    """+1 to move past the second >"""
                    self._annotate_range(blip, start + 1, end, 'style/color',
                        'rgb(255, 0, 0)')
        else:
            for start, end, tags in ranged_match_list:
                fn = self.commands.get(tags[0], None)
                if not fn:
                    """+1 to move past the second :"""
                    self._annotate_range(blip, start + 1, end, 'style/color',
                        'rgb(0, 0, 255)')
                else:
                    fn(blip, (start, end), tags[1:])

    def _annotate_range(self, blip, start, end, attr, value):
        blip.range(start, end).annotate(attr, value)
        
if __name__ == '__main__':
    gw = WrappyBot(gwconfig)
    appengine_robot_runner.run(gw)
