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

from protector.query.query import OpenTSDBQuery, OpenTSDBResponse
import time


class TestQuery(unittest.TestCase):

    def setUp(self):

        self.response1 = "[]"
        self.response2 = """
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

        self.response2_ret = [
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
            }    
        ]

        self.stats2 = {
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
            "rowsPostFilter": 129,
            "rowsPreFilter": 129,
            "successfulScan": 20,
            "uidPairsResolved": 0
        }

        self.response3 = """
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
            }    
        ]
        """


    def test_ok_empty_response(self):

        r = OpenTSDBResponse(self.response1)
        self.assertTrue(not r.get_stats())

    def test_ok_normal_response(self):

        r = OpenTSDBResponse(self.response2)

        # expected response with summary stripped
        p = json.dumps(self.response2_ret, sort_keys=True)

        # test that response summary is correctly stripped
        self.assertEqual(p, r.to_json(True))

        # test that stats are properly collected
        self.assertDictEqual(self.stats2, r.get_stats())

    def test_missing_stats_response(self):

        r = OpenTSDBResponse(self.response3)
        # no error is raised, just logged
        self.assertTrue(not r.get_stats())