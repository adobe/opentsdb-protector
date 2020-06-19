opentsdb-protector
======

### Introduction

This project was born as an effort to bring in more visibility into OpenTSDB query traffic as well as to provide
filtering and throttling capabilities for OpenTSDB queries.\
OpenTSDB does not have these capabilities (very few emerged in 2.4) and is virtually defenseless against query abuse.\
In a nutshell, opentsdb-protector aims to create a defence & insight proxy tool for OpenTSDB queries.\
Inspired by: https://github.com/trivago/Protector .

Goals:

* Prevent aggressive, poorly constructed or expensive queries to OpenTSDB that could overload the cluster.
* Offer a set of filter rules and an internal state to match, log, filter and analyze queries.
* Enforce blocked lists, allowed lists and passthrough.
* Return error messages in Grafana error format.

opentsdb-protector acts as a proxy between the query source (e.g. Grafana) and OpenTSDB.\
**It does not and should not be used to store data in OpenTSDB over HTTP (no /api/put proxying)**.

## How it works

opentsdb-protector checks each query against a list of rules before it even reaches the database.  
Filtered queries will not be executed at all and an error message will be returned instead.  
Rules can be specified in your `config.yaml`.

You can show a description of all available rules with `opentsdb-protector --show_rules`.
Here's the current list of rules:

#### Prevent queries with no aggregation (`query_no_aggregator`) ####

Queries that don't use aggregation can be responsible for high volumes of raw data being pulled from the tsdb.\
This is a stateless filter. You can use it if you choose to enforce such a policy.

#### Prevent queries with no tags or filters (`query_no_tags_filters`) ####

Using tags or filters is just a good practice since they limit the dataset being processed by the tsdb.

#### Prevent querying for very old data (`query_old_data`) ####

Such queries can impact tsdb performance because it needs to open and parse very old shards from disk.\
This is a stateless filter. A time limit can be specified in `config.yaml`.

#### Prevent too many datapoints per query (`too_many_datapoints`) ####

Such queries can impact tsdb performance or overload the client with too much data transferred over the wire.\
A limit on the data points amount can be specified in `config.yaml`. This is a stateful filter, the application will\
reject the query based on the dps amount from the last query execution.

#### Prevent queries that exceed a certain frequency (`exceed_frequency`) ####

Executing the same query (especially an expensive one) much too often usually does not bring any value \
but affects the cluster performance. This is a stateful filter, the application will \
reject the query based on the last query execution time. A max frequency can be specified in `config.yaml`

#### Prevent queries that exceed a certain execution time (`exceed_time_limit`) ####

Queries that take too long to complete can be a cause for concern. You can filter them using this rule while you investigate.\
This is a stateful filter, the application will reject the query based on the previous query duration.

#### Blockedlist

You can create a blockedlist for series names in the config. Queries for metric names matching one of the patterns will be rejected.

#### Allowedlist

You can create an allowedlist for series names in the config. If the metric name is not already on the blockedlist, it will be allowed to pass through without any filtering.

#### Safe Mode

If `safe_mode` flag is on the application will proxy all the queries without any filtering whatsoever.\
Especially useful in the beginning, for collecting statistics about the queries before imposing restrictions.

## Usage

opentsdb-protector can be run as a stand-alone Python application.

Please create a `config.yaml` with all your settings. Use the sample config file supplied in the repo `config_sample.yaml`\
to get started. Make sure to adjust the `backend_host` and `backend_port` to point to your OpenTSDB endpoint.\
You also need a Redis server for the application to store the statistics. Supply the connection information in the `db` section of the config.

You need to have Python 2.7 installed on your server

```Python
python setup.py install
opentsdb-protector -c config.yaml
```

### Wiring up

After you've started opentsdb-protector, point all your user-facing endpoints (e.g. Grafana) to it instead of OpenTSDB.  
That should do the trick.


## Commandline options

You can overwrite the following settings from the command-line:

```
usage: opentsdb-protector [-h] [--host HOST] [--port PORT]
                   [--backend_host BACKEND_HOST] [--backend_port BACKEND_PORT]
                   [-c CONFIGFILE] [-v] [--show_rules] [-f] [--version]
                   [{start,stop,status,restart}]

opentsdb-protector - Circuit breaker and analytics tool for OpenTSDB queries

positional arguments:
  {start,stop,status,restart}
                        One of the following options:
                        start: Start the daemon (default)
                        stop: Stop the daemon
                        status: Show current status
                        restart: Restart the daemon

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Hostname to bind to (default: localhost)
  --port PORT           Port to bind to (default: 8888)
  --backend_host BACKEND_HOST
                        OpenTSDB hostname (default: localhost)
  --backend_port BACKEND_PORT
                        OpenTSDB port (default: 4242)
  -c CONFIGFILE, --configfile CONFIGFILE
                        Configfile path (default: None)
  -v, --verbose         Set verbosity level. Increase verbosity by adding a v:
                        -v -vv -vvv (default: 0)
  --show_rules          Show a list of available rules and quit
  -f, --foreground      Run in foreground. Don't daemonize on start.
  --version             Show version
```

### Contributing

Contributions are welcomed! Read the [Contributing Guide](./.github/CONTRIBUTING.md) for more information.

### Licensing

This project is licensed under BSD License. See [LICENSE](LICENSE) for more information.
