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
import os

try:
    import feedparser
    import requests
except ImportError as exc:
    print('Error: failed to import module ({}). \nInstall missing modules using '
          '"sudo pip install -r requirements.txt"'.format(exc))
    sys.exit(0)

headers = {'Content-Type': 'application/json'}

saveFolder = os.getenv('APPDATA') + "\\FeedFetcher"
preferences = {}


def reload_settings():
    reload(settings)
    preferences['mattermost_webhook_url'] = settings.mattermost_webhook_url
    preferences['delay_between_pulls'] = settings.delay_between_pulls
    preferences['verify_cert'] = settings.verify_cert
    preferences['silent_mode'] = settings.silent_mode
    preferences['feeds'] = settings.feeds
    preferences['reload_settings'] = settings.reload_settings


def post_text(text, username, channel, iconurl):
    """
    Mattermost POST method, posts text to the Mattermost incoming webhook URL
    """
    data = {'text': text}
    if len(username) > 0:
        data['username'] = username
    if len(channel) > 0:
        data['channel'] = channel
    if len(iconurl) > 0:
        data['icon_url'] = iconurl

    r = requests.post(preferences['mattermost_webhook_url'], headers=headers, data=json.dumps(data),
                      verify=preferences['verify_cert'])

    if r.status_code is not requests.codes.ok:
        logging.debug('Encountered error posting to Mattermost URL %s, status=%d, response_body=%s' %
                      (preferences['mattermost_webhook_url'], r.status_code, r.json()))


if __name__ == "__main__":
    FORMAT = '%(asctime)-15s - %(message)s'
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format=FORMAT)
    reload_settings()
    if (not preferences['verify_cert']) and hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    if not os.path.exists(saveFolder):
        os.makedirs(saveFolder)
    with open(saveFolder + '\\lastFeeds.json', 'r+') as f:
        try:
            config = json.load(f)
        except:
            config = {}

    if len(preferences['mattermost_webhook_url']) == 0:
        print('mattermost_webhook_url must be configured. Please see instructions in README.md')
        sys.exit()

    uniquechannels = set([feed.Channel for feed in preferences['feeds']])
    for c in uniquechannels:
        post_text(":recycle: Python server restarted :recycle: \n\n",
                  preferences['feeds'][0].User, c, preferences['feeds'][0].Iconurl)

    while 1:
        if reload_settings:
            reload_settings()
        update = False
        for feed in preferences['feeds']:
            try:
                d = feedparser.parse(feed.Url)
                feed.NewTitle = d['entries'][0]['title']
                feed.ArticleUrl = d['entries'][0]['link']
                try:
                    feed.Description = d['entries'][0]['description']
                except:
                    pass
                configKey = feed.Url + " " + feed.Channel
                if not configKey in config.keys():
                    config[configKey] = ""
                if config[configKey] != feed.NewTitle:
                    config[configKey] = feed.NewTitle
                    update = True
                    feed.LastTitle = feed.NewTitle
                    joinedtext = feed.jointext()
                    if "(stable" in joinedtext or "(back" in joinedtext:
                        feed.NewTitle = ":white_check_mark: " + feed.NewTitle + ":white_check_mark:"
                    elif "(unstable" in joinedtext or "(abort" in joinedtext:
                        feed.NewTitle = ":warning: " + feed.NewTitle + ":warning:"
                    elif "(broken" in joinedtext:
                        feed.NewTitle = ":no_entry: " + feed.NewTitle + ":no_entry:"
                    if not preferences['silent_mode']:
                        logging.debug('Feed url: ' + feed.Url)
                        logging.debug('Title: ' + feed.NewTitle)
                        logging.debug('Link: ' + feed.ArticleUrl)
                        logging.debug('Posted text: ' + feed.jointext())
                    post_text(feed.jointext(), feed.User, feed.Channel, feed.Iconurl)

                else:
                    if not preferences['silent_mode']:
                        logging.debug('Nothing new. Waiting for good news...')
            except:
                logging.critical('Error fetching feed ' + feed.Url)
                logging.exception(sys.exc_info()[0])
        if update:
            with open(saveFolder + '\\lastFeeds.json', 'w+') as f:
                json.dump(config, f)
        time.sleep(preferences['delay_between_pulls'])
