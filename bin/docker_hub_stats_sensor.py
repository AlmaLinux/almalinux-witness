#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2020-06-06

"""
Submits a Docker Hub image usage statistics to an MQTT topic.

MQTT topic name format:

    stats/usage/dockerhub/{organization}/{image}

The program uses the JSON format to encode a message:

    {"pulls": int, "stars": int, "ts": str}

Execution example:

    $ docker_hub_stats_sensor.py -o library -i almalinux
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
        description="Docker Hub image statistics sensor"
    )
    arg_parser.add_argument('-i', '--image', required=True,
                            help='Docker image name')
    arg_parser.add_argument('-o', '--organization', required=True,
                            help='Docker Hub organization name')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_image_stats(org: str, image: str) -> dict:
    """
    Returns a Docker Hub image pulls and stars count.

    Parameters
    ----------
    org : str
        Docker Hub organization name.
    image : str
        Docker image name.

    Returns
    -------
    dict
        Dictionary containing an image pulls and stars count.
    """
    url = f'https://hub.docker.com/v2/repositories/{org}/{image}/'
    with urllib.request.urlopen(url) as request:
        j = json.load(request)
        return {'pulls': j['pull_count'],
                'stars': j['star_count'],
                'ts': get_iso8601_ts()}


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    org = args.organization
    image = args.image
    mqtt_topic = get_usage_stats_topic_name('dockerhub', org, image)
    image_stats = get_image_stats(org, image)
    #
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(image_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
