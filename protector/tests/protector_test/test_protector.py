#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

import unittest
import json

from protector.protector_main import Protector
from protector.query.query import OpenTSDBQuery
from mock import mock

p = None
stats = {}
meta = {}
q = {}

class MockRedis(object):
    def exists(self, key):
        return False

    def ping(self):
        return True

    def set(self, key, value, ex):
        q[key] = value

    def rpush(self, key, value):
        stats[key] = value

    def hexists(self, hash, key):
        return False

    def hmset(self, key, data):
        meta[key] = data

    def hincrby(self, key, hkey, value):
        meta[key][hkey] = value

    def zscore(self, z, key):
        return 1

    def zadd(self, z, value):
        return 1

@mock.patch("redis.Redis", mock.MagicMock(return_value=MockRedis()))
def get_protector():
    global p
    db_conf = {"redis": {"host":"", "port":"", "password":""}}
    p = Protector({"query_no_aggregator": None}, [], [], db_conf, False)


class TestProtector(unittest.TestCase):

    def setUp(self):

        if not p:
            get_protector()

        self.payload1 = """
                        {
                          "start": "3m-ago",
                          "queries": [
                            {
                              "metric": "mymetric.received.P95",
                              "aggregator": "max",
                              "downsample": "20s-max",
                              "filters": [
                                {
                                  "filter": "DEV",
                                  "groupBy": false,
                                  "tagk": "environment",
                                  "type": "iliteral_or"
                                }
                              ]
                            }
                          ]
                        }
                        """

        self.payload2 = """
                        {
                          "start": "3m-ago",
                          "queries": [
                            {
                              "metric": "a.mymetric.received.P95",
                              "aggregator": "max",
                              "downsample": "20s-max",
                              "filters": []
                            }
                          ]
                        }
                        """

        self.payload3 = """
                        {
                          "start": "3m-ago",
                          "queries": [
                            {
                              "metric": "mymetric",
                              "aggregator": "max",
                              "downsample": "20s-max",
                              "filters": []
                            }
                          ]
                        }
                        """

        self.payload4 = """
                        {
                          "start": "3m-ago",
                          "queries": [
                            {
                              "metric": "mymetric",
                              "aggregator": "none",
                              "downsample": "20s-max",
                              "filters": []
                            }
                          ]
                        }
                        """

        self.response = """
        [
            {
                "metric": "this.metric",
                "tags": {
                    "env": "prod",
                    "recipientDomain": "gmail.com",
                    "channel": "email"
                },
                "aggregateTags": [
                    "hostname"
                ],
                "dps": {
                    "1623619500": 0,
                    "1623619560": 0,
                    "1623619620": 0
                }
            },
            {
                "metric": "this.metric",
                "tags": {
                    "env": "prod",
                    "recipientDomain": "gmail.com",
                    "channel": "email"
                },
                "aggregateTags": [
                    "hostname"
                ],
                "dps": {
                    "1623619500": 0,
                    "1623619560": 0,
                    "1623619620": 0
                }
            },
            {
                "statsSummary": {
                    "avgAggregationTime": 0.806912,
                    "avgHBaseTime": 3.874463,
                    "avgQueryScanTime": 5.436076,
                    "avgScannerTime": 3.888163,
                    "avgScannerUidToStringTime": 0,
                    "avgSerializationTime": 0.808312,
                    "dpsPostFilter": 145,
                    "dpsPreFilter": 145,
                    "emittedDPs": 1440,
                    "maxAggregationTime": 0.806912,
                    "maxHBaseTime": 5.170471,
                    "maxQueryScanTime": 5.436076,
                    "maxScannerUidToStringTime": 0,
                    "maxSerializationTime": 0.808312,
                    "maxUidToStringTime": 0.0255,
                    "processingPreWriteTime": 8.480518,
                    "queryIdx_00": {
                        "aggregationTime": 0.806912,
                        "avgHBaseTime": 3.874463,
                        "avgScannerTime": 3.888163,
                        "avgScannerUidToStringTime": 0,
                        "dpsPostFilter": 145,
                        "dpsPreFilter": 145,
                        "emittedDPs": 1440,
                        "groupByTime": 0,
                        "maxHBaseTime": 5.170471,
                        "maxScannerUidToStringTime": 0,
                        "queryIndex": 0,
                        "queryScanTime": 5.436076,
                        "rowsPostFilter": 129,
                        "rowsPreFilter": 129,
                        "saltScannerMergeTime": 0.163702,
                        "serializationTime": 0.808312,
                        "successfulScan": 20,
                        "uidPairsResolved": 0,
                        "uidToStringTime": 0.0255
                    },
                    "rowsPostFilter": 129,
                    "rowsPreFilter": 129,
                    "successfulScan": 20,
                    "uidPairsResolved": 0
                }
            }
        ]
        """

    def test_blockedlist(self):

        p.blockedlist = ["^releases$", "^mymetric\.", ".*java.*boot.*version.*"]

        self.assertFalse(p.check(OpenTSDBQuery(self.payload1)).is_ok())
        self.assertTrue(p.check(OpenTSDBQuery(self.payload2)).is_ok())
        self.assertTrue(p.check(OpenTSDBQuery(self.payload3)).is_ok())

        p.blockedlist = []
        self.assertTrue(p.check(OpenTSDBQuery(self.payload1)).is_ok())

    def test_safe_mode(self):

        p.blockedlist = ["^releases$", "^mymetric"]
        p.safe_mode = True

        self.assertFalse(p.check(OpenTSDBQuery(self.payload4)).is_ok())

        p.safe_mode = False
        self.assertFalse(p.check(OpenTSDBQuery(self.payload4)).is_ok())

    def test_invalid_queries(self):

        p.safe_mode = False

        with self.assertRaisesRegexp(Exception, 'Invalid OpenTSDB query'):
            p.check(OpenTSDBQuery('{}'))

        with self.assertRaisesRegexp(Exception, 'Invalid OpenTSDB query'):
            p.check(OpenTSDBQuery('{"start": ""}'))

    def test_save_stats_timeout(self):

        q3 = OpenTSDBQuery(self.payload3)
        interval = int((q3.get_end_timestamp() - q3.get_start_timestamp()) / 60)

        p.save_stats(q3, None, 20, True)

        j = stats["{}_{}".format(q3.get_id(), 'stats')]
        oj = json.loads(j)

        # _stats
        self.assertTrue(oj['timeout'])
        self.assertEqual(oj['duration'], 20)
        self.assertDictEqual(oj['summary'], {})

        # _query
        qx = q["{}_{}".format(q3.get_id(), 'query')]
        qs = json.dumps(json.loads(qx), sort_keys=True)

        self.assertEqual(qs, q3.to_json(True))

        # _interval
        ki = meta["{}_{}".format(q3.get_id(), interval)]
        t = ki['timestamp']

        self.assertEqual(ki['timeout_counter'], 1)
        self.assertEqual(ki['total_counter'], 1)
        self.assertEqual(t, ki['timeout_last'])
        self.assertEqual(t, ki['first_occurrence'])
