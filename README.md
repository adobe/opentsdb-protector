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

### Contributing

Contributions are welcomed! Read the [Contributing Guide](./.github/CONTRIBUTING.md) for more information.

### Licensing

This project is licensed under BSD License. See [LICENSE](LICENSE) for more information.
