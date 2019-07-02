DEFAULT_CONFIG = {
    # Protector server address
    'host': 'localhost',
    'port': 8888,
    # Connection to the time series database API
    'backend_host': 'localhost',
    'backend_port': 8086,
    'rules': {
        'query_no_tags_filters': None,
        'query_no_aggregator': None,
        'too_many_datapoints': 10000,
        'query_old_data': 90,
        'exceed_time_limit': 20,
        'exceed_frequency': 30
    },
    # Queries for series names matching one of
    # the following patterns will be rejected
    'blacklist': [],
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
