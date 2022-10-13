#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2022-10-13

"""
Submits DistroWatch last 7 days rank and hits count for the specified
distribution to an MQTT topic.

MQTT topic name format:

    stats/social/distrowatch/{organization}'

The program uses the JSON format to encode a message:

    {"rank": int, "hits": int, "ts": "str"}

Execution example:

    $ distrowatch_stats_sensor.py -o 'almalinux'
"""

import argparse
import json
import sys
import typing
import urllib.request

import lxml.etree
import paho.mqtt.client


from almawitness.sensors.common import (
    add_mqtt_arg_parser_args,
    get_iso8601_ts,
    mqtt_client
)


def init_arg_parser() -> argparse.ArgumentParser:
    """
    Creates and initializes a command line arguments parser.

    Returns:
        Command line arguments parser.
    """
    arg_parser = argparse.ArgumentParser(
        description="DistroWatch page hit ranking statistics sensor"
    )
    arg_parser.add_argument('-o', '--organization', required=True,
                            help='Organization (distribution) name. It will '
                                 'be sent to an MQTT topic.')
    arg_parser.add_argument('--query',
                            help='OS name as it shown on the DistroWatch. '
                                 'Default value is the organization name.')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_distro_stats(os_name: str) -> typing.Optional[typing.Dict]:
    """
    Returns DistroWatch last 7 days hits and rank for the specified
    distribution.

    Args:
        os_name: Distribution name as it specified on DistroWatch.

    Returns:
        Dictionary containing a distribution rank and hits count.
    """
    rsp = urllib.request.urlopen('https://distrowatch.com/index.php?dataspan=1')
    root = lxml.etree.fromstring(rsp.read(), lxml.etree.HTMLParser())
    xpath_q = (f'//table[@class="News"]/tr/th[text()="Page Hit Ranking"]/'
               f'../../tr/td[@class="phr2"]/'
               f'a[re:test(text(), "{os_name}", "i")]/../..')
    ns = {'re': 'http://exslt.org/regular-expressions'}
    for row in root.xpath(xpath_q, namespaces=ns):
        rank = row.xpath('./th[@class="phr1"]/text()')[0]
        hits = row.xpath('./td[@class="phr3"]/text()')[0]
        return {'rank': int(rank),
                'hits': int(hits),
                'ts': get_iso8601_ts()}


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    org = args.organization
    mqtt_topic = f'stats/social/distrowatch/{org}'
    query = args.query
    stats = get_distro_stats(query if query else org)
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
