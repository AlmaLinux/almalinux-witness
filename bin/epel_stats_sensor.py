#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Igor Seletskiy <iseletsk@almalinux.org>
# created: 2022-05-15

"""
EPEL hits statistics to an MQTT topic.
https://data-analysis.fedoraproject.org/csv-reports/countme/totals.db

MQTT topic name format:

    stats/social/epel/{os}

Known OSes:
AlmaLinux
Almalinux

CloudLinux

EuroLinux

Oracle Linux
Oracle Linux Server
OracleLinux

SUSE Liberty Linux
Virtuozzo
Virtuozzo Hybrid Server
Virtuozzo Linux

Rocky
Rocky Linux
Rocky Linux Stream

Note that this is case insentive, and you can use % wildcard, like Rocky% or Virtuozzo%

The program uses the JSON format to encode a message:

    {
      "hits": int,
      "ts": str
    }

The `hits` field gives number of hits for a week from EPEL

Execution example:

    $ epel_stats_sensor.py -o AlmaLinux
"""

import argparse
import json
import sys
import typing
import urllib.request
import os.path
import time
import sqlite3

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
        description="EPEL community statistics sensor"
    )
    arg_parser.add_argument('-o', '--os', required=True,
                            help='OS name')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser

def is_file_older_than_x_days(file, days=1):
    file_time = os.path.getmtime(file)
    # Check against 24 hours
    return ((time.time() - file_time) / 3600 > 24*days)

def get_epel_stats(os_name: str) -> dict:
    """
    Returns # of hits for OS.

    Parameters
    ----------
    os : str
        OS name.

    Returns
    -------
    dict
        Dictionary containing a subreddit user activity statistics.
    """

    target_name = f'./totals.db'
    if not os.path.exists(target_name) or os.stat(target_name).st_size == 0 or is_file_older_than_x_days(target_name, 1):
        url = 'https://data-analysis.fedoraproject.org/csv-reports/countme/totals.db'
        u = urllib.request.urlretrieve(url, target_name)

    with sqlite3.connect(target_name) as con:
        cur = con.cursor()
        cur.execute("select sum(hits) from countme_totals where upper(os_name) like ? and repo_tag like 'epel%' "
                    "group by weeknum order by weeknum desc limit 1", [os_name.upper()])
        row = cur.fetchone()
        stats = { 'hits': row[0],
                  'ts': get_iso8601_ts()}
        return stats


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    os_name = args.os
    mqtt_topic = f'stats/social/epel/{os_name}'
    epel_stats = get_epel_stats(os_name)
    #
    # import pprint
    # pprint.pprint(epel_stats)
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(epel_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))