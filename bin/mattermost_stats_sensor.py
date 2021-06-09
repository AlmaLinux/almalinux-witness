#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2021-06-09

"""
Submits a Mattermost chat server statistics to an MQTT topic.

MQTT topic name format:

    stats/social/{chat_server}

The program uses the JSON format to encode a message:

    {
      "total_users": int,
      "active_users": int,
      "monthly_active_users": int,
      "banned_users": int,
      "ts": str
    }

The following data is reported:

  * total_users - total registered users count
  * active_users - daily active users count
  * monthly_active_users - monthly active users count
  * banned_users - total banned users count

Execution example:

    $ mattermost_stats_sensor.py -c chat.almalinux.org -t YOUR_TOKEN_HERE
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

import paho.mqtt.client

from almawitness.sensors.common import (
    add_mqtt_arg_parser_args,
    get_iso8601_ts,
    mqtt_client
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
        description="Mattermost chat statistics sensor"
    )
    arg_parser.add_argument('-c', '--chat-server', required=True,
                            help='Mattermost chat server domain name or IP '
                                 'address')
    arg_parser.add_argument('-t', '--token', required=True,
                            help='Authentication token')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_mattermost_stats(server: str, token: str) -> dict:
    """
    Returns a Mattermost chat server statistics.

    Parameters
    ----------
    server : str
        Mattermost server domain name or IP address.
    token : str
        Authentication token.

    Returns
    -------
    dict
        Dictionary containing a chat server statistics.
    """
    url = f'https://{server}/api/v4/analytics/old'
    params = urllib.parse.urlencode({'name': 'standard'})
    headers = {'Authorization': f'Bearer {token}',
               'Content-Type': 'application/json'}
    rqst = urllib.request.Request(f'{url}?{params}', headers=headers)
    mapping = {
        'unique_user_count': 'total_users',
        'daily_active_users': 'active_users',
        'monthly_active_users': 'monthly_active_users',
        'inactive_user_count': 'banned_users'
    }
    with urllib.request.urlopen(rqst) as request:
        stats = {'ts': get_iso8601_ts()}
        for rec in json.load(request):
            if rec['name'] in mapping:
                stats[mapping[rec['name']]] = rec['value']
        return stats


def main(sys_args: list):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    chat_server = args.chat_server
    mqtt_topic = f'stats/social/{chat_server}'
    chat_stats = get_mattermost_stats(chat_server, args.token)
    #
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(chat_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
