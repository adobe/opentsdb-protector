#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

DEFAULT_CONFIG = {
    # Protector server address
    'host': 'localhost',
    'port': 8888,
    # Connection to the time series database API
    'backend_host': 'localhost',
    'backend_port': 4242,
    'safe_mode': False,
    'rules': {
        'query_no_tags_filters': None,
        'query_no_aggregator': None,
        'too_many_datapoints': 10000,
        'query_old_data': 90,
        'exceed_time_limit': {
            'limit': 20,
            'throttle': 300
        },
        'exceed_frequency': 30
    },
    # Queries for series names matching one of
    # the following patterns will be rejected
    'blockedlist': [],
    # Queries for series names matching one of
    # the following patterns will skip the filters (if not rejected by the blockedlist!)
    'allowedlist': [],
    # Run in foreground?
    'foreground': False,
    # Default PID file location
    'pidfile': '/var/run/protector.pid',
    'logfile': '/var/log/protector.log',
    'configfile': None,
    'c': None,
    'verbose': 0,
    'v': 0,
}
