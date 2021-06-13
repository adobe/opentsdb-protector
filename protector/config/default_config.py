DEFAULT_CONFIG = {
    # Protector server address
    'host': 'localhost',
    'port': 8888,
    # Connection to the time series database API
    'backend_host': 'localhost',
    'backend_port': 8086,
    'rules': [
        'query_no_tags_filters',
        'query_no_aggregator',
        'too_many_datapoints',
        'query_old_data'
    ],
    # Queries for series names matching one of
    # the following patterns are always executed
    # without any checking
    'blacklist': [],
    # Run in foreground?
    'foreground': False,
    # Default PID file location
    'pidfile': '/var/run/protector.pid',
    'logfile': '/var/log/protector.log',
    # Smallest possible system date.
    # This is required for the calculation of the max duration between datetime objects.
    # We use the release day of InfluxDB 0.8 as the epoch by default
    # because it is the first official version supported.
    # You can overwrite it with this parameter, though:
    'epoch': None,
    'configfile': None,
    'c': None,
    'verbose': 0,
    'v': 0,
}
