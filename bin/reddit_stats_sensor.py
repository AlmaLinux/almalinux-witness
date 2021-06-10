#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2021-06-10

"""
Submits a Reddit community statistics to an MQTT topic.

MQTT topic name format:

    stats/social/reddit/{subreddit}

The program uses the JSON format to encode a message:

    {
      "total_users": int,
      "active_users": int,
      "ts": str
    }

The `active_users` field is optional and will be present only of Reddit API
returns false value for the `accounts_active_is_fuzzed` field. Otherwise,
the `active_users` number is not accurate and should be ignored.

Execution example:

    $ reddit_stats_sensor.py -r AlmaLinux
"""

import argparse
import json
import sys
import typing
import urllib.request

import paho.mqtt.client

from almawitness.sensors.common import (
    add_mqtt_arg_parser_args,
    get_iso8601_ts,
    mqtt_client,
    USER_AGENT
)


def init_arg_parser() -> argparse.ArgumentParser:
    """
    Creates and initializes a command line arguments parser.

    Returns
    -------
    argparse.ArgumentParser
        Command line arguments parser.
    """
    arg_parser = argparse.ArgumentParser(
        description="Reddit community statistics sensor"
    )
    arg_parser.add_argument('-r', '--reddit', required=True,
                            help='Subreddit name')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_reddit_stats(subreddit: str) -> dict:
    """
    Returns a subreddit user activity statistics.

    Parameters
    ----------
    subreddit : str
        Subreddit name.

    Returns
    -------
    dict
        Dictionary containing a subreddit user activity statistics.
    """
    url = f'https://www.reddit.com/r/{subreddit}/about.json'
    rqst = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(rqst) as request:
        data = json.load(request)['data']
        stats = {'total_users': data['subscribers'],
                 'ts': get_iso8601_ts()}
        if not data['accounts_active_is_fuzzed']:
            stats['active_users'] = data['active_user_count']
        return stats


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    subreddit = args.reddit
    mqtt_topic = f'stats/social/reddit/{subreddit}'
    reddit_stats = get_reddit_stats(subreddit)
    #
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(reddit_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
