#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'elpatron@mailbox.org'
# Partially derived from https://github.com/mattermost/mattermost-integration-gitlab

import json
import time
import sys
import logging
import settings
import ssl
try:
    import feedparser
    import requests
except ImportError as exc:
    print('Error: failed to import module ({}). \nInstall missing modules using '
          '"sudo pip install -r requirements.txt"'.format(exc))
    sys.exit(0)

settings = {}
settings['mattermost_webhook_url'] = settings.mattermost_webhook_url
settings['delay_between_pulls'] = settings.delay_between_pulls
settings['verify_cert'] = settings.verify_cert
settings['silent_mode'] = settings.silent_mode
settings['feeds'] = settings.feeds
settings['reload_settings'] = settings.reload_settings
headers = {'Content-Type': 'application/json'}

if (not settings['verify_cert']) and hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


def reload_settings():
    reload(settings)
    settings['mattermost_webhook_url'] = settings.mattermost_webhook_url
    settings['delay_between_pulls'] = settings.delay_between_pulls
    settings['verify_cert'] = settings.verify_cert
    settings['silent_mode'] = settings.silent_mode
    settings['feeds'] = settings.feeds
    settings['reload_settings'] = settings.reload_settings


def post_text(text, username, channel, iconurl):
    """
    Mattermost POST method, posts text to the Mattermost incoming webhook URL
    """
    data = {}
    data['text'] = text
    if len(username) > 0:
        data['username'] = username
    if len(channel) > 0:
        data['channel'] = channel
    if len(iconurl) > 0:
        data['icon_url'] = iconurl

    r = requests.post(settings['mattermost_webhook_url'], headers=headers, data=json.dumps(data), verify=settings['verify_cert'])

    if r.status_code is not requests.codes.ok:
        logging.debug('Encountered error posting to Mattermost URL %s, status=%d, response_body=%s' %
                      (settings['mattermost_webhook_url'], r.status_code, r.json()))


if __name__ == "__main__":
    FORMAT = '%(asctime)-15s - %(message)s'
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format=FORMAT)
    if len(settings['mattermost_webhook_url']) == 0:
        print('mattermost_webhook_url must be configured. Please see instructions in README.md')
        sys.exit()


    uniquechannels = set([feed.Channel for feed in settings['feeds']])
    for c in uniquechannels:
        post_text(":recycle: Python server restarted :recycle: \n\nIt can be that whatever follows, is not new", settings['feeds'][0].User,c,settings['feeds'][0].Iconurl)

    started=False
    while 1:
        if reload_settings:
            reload_settings()
        for feed in settings['feeds']:
            try:
                d = feedparser.parse(feed.Url)
                feed.NewTitle = d['entries'][0]['title']
                feed.ArticleUrl = d['entries'][0]['link']
                try:
                    feed.Description = d['entries'][0]['description']
                except:
                    pass
                if feed.LastTitle != feed.NewTitle:
                    feed.LastTitle = feed.NewTitle
                    joinedtext = feed.jointext()
                    if "(stable" in joinedtext or "(back" in joinedtext:
                        feed.NewTitle = ":white_check_mark: " + feed.NewTitle + ":white_check_mark:"
                    elif "(unstable" in joinedtext or "(abort" in joinedtext:
                        feed.NewTitle = ":warning: " + feed.NewTitle + ":warning:"
                    elif "(broken" in joinedtext:
                        feed.NewTitle = ":no_entry: " + feed.NewTitle + ":no_entry:"
                    if not settings['silent_mode']:
                        logging.debug('Feed url: ' + feed.Url)
                        logging.debug('Title: ' + feed.NewTitle)
                        logging.debug('Link: ' + feed.ArticleUrl)
                        logging.debug('Posted text: ' + feed.jointext())
                    post_text(feed.jointext(), feed.User, feed.Channel, feed.Iconurl)
                    
                else:
                    if not settings['silent_mode']:
                        logging.debug('Nothing new. Waiting for good news...')
            except:
                logging.critical('Error fetching feed ' + feed.Url)
                logging.exception(sys.exc_info()[0])
        if not started:
            for c in uniquechannels:
                post_text(":recycle: Python server has finished restarting :recycle: \n\nBack to normal",
                          settings['feeds'][0].User,c,settings['feeds'][0].Iconurl)
        started=True
        time.sleep(settings['delay_between_pulls'])
