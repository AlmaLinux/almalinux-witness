#!/usr/bin/env python3
# -*- mode:python; coding:utf-8; -*-
# author: Eugene Zamriy <ezamriy@almalinux.org>
# created: 2021-06-08

"""Common functions used by AlmaLinux Witness sensors."""

import argparse
import contextlib
import datetime

import paho.mqtt.client

__all__ = [
    'add_mqtt_arg_parser_args', 'get_iso8601_ts', 'get_usage_stats_topic_name',
    'mqtt_client'
]


def add_mqtt_arg_parser_args(arg_parser: argparse.ArgumentParser,
                             server: str = 'localhost',
                             port: int = 1883,
                             qos: int = 1):
    """
    Adds MQTT-specific command line arguments to an argument parser.

    Parameters
    ----------
    arg_parser : argparse.ArgumentParser
        Command line arguments parser.
    server : str, optional
        Default MQTT server hostname or IP address.
    port : int, optional
        Default MQTT server TCP port.
    qos : int, optional
        Default QoS level for MQTT protocol.
    """
    arg_parser.add_argument('-s', '--server', default=server,
                            help=f'MQTT server hostname or IP address. '
                                 f'Default is {server}')
    arg_parser.add_argument('-p', '--port', default=port, type=int,
                            help=f'MQTT server TCP port. Default is {port}')
    arg_parser.add_argument('-q', '--qos', default=qos, type=int,
                            help=f'MQTT Quality of Service level to use. '
                                 f'Default is {qos}')


def get_iso8601_ts() -> str:
    """
    Returns current UTC timestamp in the ISO 8601 format.

    Returns
    -------
    str
    """
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_usage_stats_topic_name(platform: str, org: str,  image: str) -> str:
    """
    Generates an MQTT topic name for distribution usage statistics.

    Parameters
    ----------
    platform : str
        Monitored platform name (e.g. dockerhub).
    org: str
        Organization or user name.
    image : str
        Docker image name.

    Returns
    -------
    str
        MQTT topic name.
    """
    return f'stats/usage/{platform}/{org}/{image}'


@contextlib.contextmanager
def mqtt_client(server: str, port: int):
    """
    MQTT client context manager.

    Parameters
    ----------
    server : str
        MQTT server hostname or IP address.
    port : int
        MQTT server port.
    """
    cli = paho.mqtt.client.Client()
    cli.connect(server, port)
    cli.loop_start()
    try:
        yield cli
    finally:
        cli.disconnect()
