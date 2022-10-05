#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Igor Seletskiy <iseletsk@almalinux.org>
#         Eugene Zamriy <ezamriy@almalinux.org>
# created: 2022-05-15

"""
Submits last week EPEL hits statistics to an MQTT topic.

Data source:

    https://data-analysis.fedoraproject.org/csv-reports/countme/totals.db

MQTT topic name format:

    stats/usage/epel/{organization}/{distro_ver}

The sensor will send a message for each version of a distribution and a message
with total hits number for all versions. The total message will be sent to the
`stats/usage/epel/{organization/all` topic.

The program uses the JSON format to encode a message:

    {"hits": int, "ts": str}

The `hits` field gives number of hits for the last week from EPEL.

Execution example:

    $ epel_stats_sensor.py -o almalinux --query 'almalinux%%'

Note that OS name is case-insensitive, and you can use % wildcard, like Rocky%
or Virtuozzo%.
"""

import argparse
import json
import os.path
import re
import sqlite3
import sys
import time
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

    Returns:
        Command line arguments parser.
    """
    arg_parser = argparse.ArgumentParser(
        description="EPEL community statistics sensor"
    )
    arg_parser.add_argument('-d', '--db-path', default='epel-totals.db',
                            help='EPEL countme database download file path. '
                                 'Default is epel-totals.db')
    arg_parser.add_argument('-o', '--organization', required=True,
                            help='Organization (distribution) name. It will '
                                 'be used for grouping all matching records '
                                 'under the same name')
    arg_parser.add_argument(
        '--query',
        help='OS name query for EPEL countme database. Sqlite wildcards are '
             'supported (e.g. "almalinux%%"). Default value is the '
             'organization name'
    )
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def is_file_outdated(file_path: str, expire_days: int) -> bool:
    """
    Checks if the specified file is outdated.

    Args:
        file_path: file path.
        expire_days: file expiration time in days.

    Returns:
        True if file is outdated, False otherwise.
    """
    return (time.time() - os.path.getmtime(file_path)) / 3600 > 24 * expire_days


def download_db(db_path: str, expire_days: int = 1) -> str:
    """
    Downloads an EPEL countme database file if it is missing or outdated.

    Args:
        db_path: database file download path.
        expire_days: database file expiration time in days. The outdated file
                     will be re-downloaded automatically.

    Returns:
        Downloaded file normalized path.
    """
    db_url = ('https://data-analysis.fedoraproject.org/csv-reports/'
              'countme/totals.db')
    target_path = os.path.abspath(
        os.path.expandvars(os.path.expanduser(db_path))
    )
    if (not os.path.exists(target_path) or os.stat(target_path).st_size == 0
            or is_file_outdated(target_path, expire_days)):
        urllib.request.urlretrieve(db_url, db_path)
    return target_path


def get_epel_stats(db_path: str,
                   os_name: str) -> typing.Generator[dict, None, None]:
    """
    Returns a last week number of EPEL hits for the specified OS.

    Args:
        db_path: EPEL countme database file path.
        os_name: Operating system name. Sqlite wildcards are supported.

    Returns:
        Generator of dictionaries containing number of EPEL hits for each
        OS version.
    """
    def regexp(pattern, string) -> int:
        return 1 if re.search(pattern, string) else 0
    sql = """
      SELECT sum(hits), repo_tag, weeknum
        FROM countme_totals
        WHERE upper(os_name) LIKE ?
              AND weeknum = (SELECT weeknum FROM countme_totals
                               ORDER BY weeknum DESC LIMIT 1)
              AND repo_tag REGEXP '^epel-\\d+$'
        GROUP BY repo_tag
    """
    ts = get_iso8601_ts()
    with sqlite3.connect(db_path) as con:
        con.create_function('regexp', 2, regexp)
        cur = con.execute(sql, (os_name.upper(),))
        total = 0
        for row in cur:
            re_rslt = re.search(r'epel-(\d+)$', row[1])
            if not re_rslt:
                raise ValueError(f'can not extract distribution version from '
                                 f'EPEL repo name: {row[1]}')
            distro_ver = re_rslt.group(1)
            hits = row[0]
            total += hits
            yield {'hits': hits, 'ts': ts, 'version': distro_ver}
        yield {'hits': total, 'ts': ts, 'version': 'all'}


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    org = args.organization
    name_query = args.query
    db_path = download_db(args.db_path)
    with mqtt_client(args.server, args.port) as mqtt_cli:
        for rec in get_epel_stats(db_path, name_query if name_query else org):
            distro_ver = rec.pop('version')
            mqtt_topic = get_usage_stats_topic_name('epel', org, distro_ver)
            print(f'Submitting {rec} to MQTT topic {mqtt_topic}')
            message_info = mqtt_cli.publish(mqtt_topic, json.dumps(rec),
                                            qos=args.qos)
            message_info.wait_for_publish()
            assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
