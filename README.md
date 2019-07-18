opentsdb-protector
======

### Introduction

This project was born as an effort to bring in more visibility into OpenTSDB query traffic as well as to provide
filtering and throttling capabilities for opentsdb queries.\
OpenTSDB does not have these capabilities (very few emerged in 2.4) and is virtually defenseless against query abuse.\
In a nutshell, opentsdb-protector aims to create a defence & insight proxy tool for OpenTSDB queries.\
Inspired by: https://github.com/trivago/Protector

Goals:

* Prevent aggresive, poorly constructed or expensive queries to OpenTSDB that could overload the cluster.
* Offer a set of filter rules and an internal state to match, log, filter and analyze queries
* Offer blacklisting, whitelisting and passthrough
* Return error messages in Grafana error format

opentsdb-protector acts as a proxy between the query source (e.g. Grafana) and OpenTSDB.\
**It does not and should not be used to store data in OpenTSDB over HTTP (no /api/put proxying)**

## How it works

opentsdb-protector checks each query against a list of rules before it even reaches the database.  
Filtered queries will not be executed at all and an error message will be returned instead.  
Rules can be specified in your `config.yaml`.

You can show a description of all available rules with `opentsdb-protector --show_rules`.
Here's the current list of rules:

#### Prevent queries with no aggregation (`query_no_aggregator`) ####
Queries that don't use aggregation can be responsible for high volumes of raw data being pulled from the tsdb.\
This is a stateless filter. You can use it if you choose to enforce such a policy

#### Prevent queries with no tags or filters (`query_no_tags_filters`) ####
Using tags or filters is just a good practice since they limit the dataset being processed by the tsdb.

#### Prevent querying for very old data (`query_old_data`) ####
Such queries can impact tsdb performance because it needs to open and parse very old shards from disk.\
This is a stateless filter. A time limit can be specified in `config.yaml`

#### Prevent too many datapoints per query (`too_many_datapoints`) ####
Such queries can impact tsdb performance or overload the client with too much data transferred over the wire.\
A limit on the data points amount can be specified in `config.yaml`. This is a stateful filter, the application will\
reject the query based on the dps amount from the last query execution

#### Prevent queries that exceed a certain frequency (`exceed_frequency`) ####
Executing the same query (especially an expensive one) much too often usually does not bring any value \
but affects the cluster performance. This is a stateful filter, the application will \
reject the query based on the last query execution time. A max frequency can be specified in `config.yaml`

#### Prevent queries that exceed a certain execution time (`exceed_time_limit`) ####
Queries that take too long to complete can be a cause for concern. You can filter them using this rule while you investigate.\
This is a stateful filter, the application will reject the query based on the previous query duration

### Contributing

Contributions are welcomed! Read the [Contributing Guide](./.github/CONTRIBUTING.md) for more information.

### Licensing

This project is licensed under BSD License. See [LICENSE](LICENSE) for more information.
