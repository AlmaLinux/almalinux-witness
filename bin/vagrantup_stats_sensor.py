#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2021-06-08

"""
Submits a Vagrant Cloud Box usage statistics to an MQTT topic.

MQTT topic name format:

    stats/usage/vagrantup/{organization}/{box_name}

The program uses the JSON format to encode a message:

    {"pulls": int, "ts": str}

Execution example:

    $ vagrantup_stats_sensor.py -i 8 -o almalinux
"""

import argparse
import json
import sys
import urllib.request

import paho.mqtt.client

from almawitness.sensors.common import (
    add_mqtt_arg_parser_args,
    get_iso8601_ts,
    get_usage_stats_topic_name,
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
        description="Vagrant box statistics sensor"
    )
    arg_parser.add_argument('-i', '--image', required=True,
                            help='Vagrant box name')
    arg_parser.add_argument('-o', '--organization', required=True,
                            help='Vagrant Cloud organization or user name')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_box_stats(org: str, box_name: str) -> dict:
    """
    Returns a Vagrant box downloads count.

    Parameters
    ----------
    org : str
        Vagrant Cloud organization or user name.
    box_name : str
        Vagrant box name.

    Returns
    -------
    dict
        Dictionary containing a box downloads count.
    """
    url = f'https://app.vagrantup.com/api/v1/user/{org}/'
    with urllib.request.urlopen(url) as request:
        j = json.load(request)
        for box in j.get('boxes', ()):
            if box['name'] == box_name:
                return {'pulls': box['downloads'],
                        'ts':  get_iso8601_ts()}
    raise Exception(f'box {org}/{box_name} is not found')


def main(sys_args):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    org = args.organization
    box_name = args.image
    mqtt_topic = get_usage_stats_topic_name('vagrantup', org, box_name)
    box_stats = get_box_stats(org, box_name)
    #
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(box_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
