#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2021-06-18

"""
Submits a GitHub repository popularity metrics to an MQTT topic.

MQTT topic name format:

    stats/usage/github/{organization}/{repository_name}

The program uses the JSON format to encode a message:

    {
      "forks": int,
      "open_issues": int,
      "stars": int,
      "subscribers": int,
      "ts": str
    }

Execution example:

    $ github_repo_stats_sensor.py -o AlmaLinux -r almalinux-deploy
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
    mqtt_client,
    USER_AGENT
)


def init_arg_parser() -> argparse.ArgumentParser:
    """
    Creates and initializes a command line arguments parser.

    Returns:
        Command line arguments parser.
    """
    arg_parser = argparse.ArgumentParser(
        description="GitHub repository popularity sensor"
    )
    arg_parser.add_argument('-o', '--organization', required=True,
                            help='GitHub organization or user name')
    arg_parser.add_argument('-r', '--repo', required=True,
                            help='GitHub repository name')
    add_mqtt_arg_parser_args(arg_parser)
    return arg_parser


def get_github_repo_stats(org: str, repo: str) -> typing.Dict:
    """
    Returns a GitHub repository popularity metrics.

    Args:
        org: GitHub organization name.
        repo: GitHub repository name.

    Returns:
        Dictionary containing a GitHub repository popularity metrics.
    """
    url = f'https://api.github.com/repos/{org}/{repo}'
    rqst = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(rqst) as request:
        data = json.load(request)
        return {'forks': data['forks'],
                'open_issues': data['open_issues_count'],
                'stars': data['stargazers_count'],
                'subscribers': data['subscribers_count'],
                'ts': get_iso8601_ts()}


def main(sys_args: typing.List[str]):
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args(sys_args)
    org = args.organization
    repo = args.repo
    mqtt_topic = f'stats/social/github/{org}/{repo}'
    repo_stats = get_github_repo_stats(org, repo)
    #
    with mqtt_client(args.server, args.port) as mqtt_cli:
        message_info = mqtt_cli.publish(mqtt_topic, json.dumps(repo_stats),
                                        qos=args.qos)
        message_info.wait_for_publish()
        assert message_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
