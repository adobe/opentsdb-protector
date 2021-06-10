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

from protector.rules import exceed_time_limit
from protector.query.query import OpenTSDBQuery
from protector.config import default_config
import time


class TestQueryExceedFrequency(unittest.TestCase):

    def setUp(self):

        config = {'limit': 20, 'throttle': 300}
        self.exceed_time_limit = exceed_time_limit.RuleChecker(config)

        self.payload1 = """
                        {
                          "start": 1530695685,
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
                          "start": "3n-ago",
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
                          "start": "90d-ago",
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
                          "start": "89d-ago",
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

    def test_below(self):

        current_time = int(round(time.time()))

        q = OpenTSDBQuery(self.payload1)
        q.set_stats({'duration': 1.5, 'timestamp': current_time - 1})

        self.assertTrue(self.exceed_time_limit.check(q).is_ok())

    def test_above(self):

        current_time = int(round(time.time()))

        q = OpenTSDBQuery(self.payload2)
        q.set_stats({'duration': 20, 'timestamp': current_time - 310})

        self.assertTrue(self.exceed_time_limit.check(q).is_ok())

        q.set_stats({'duration': 20, 'timestamp': current_time - 210})
        self.assertFalse(self.exceed_time_limit.check(q).is_ok())

    def test_none(self):

        q = OpenTSDBQuery(self.payload3)

        self.assertTrue(self.exceed_time_limit.check(q).is_ok())

class TestAdaptiveThrottling(unittest.TestCase):

    def setUp(self):

        config = {'adaptive': 1.6}
        self.adaptive_time_limit = exceed_time_limit.RuleChecker(config)

        self.payload1 = """
                        {
                          "start": 1530695685,
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

    def test_adaptive(self):

        current_time = int(round(time.time()))

        q = OpenTSDBQuery(self.payload1)
        q.set_stats({'duration': 10, 'timestamp': current_time - 16})
        self.assertTrue(self.adaptive_time_limit.check(q).is_ok())

        q.set_stats({'duration': 10, 'timestamp': current_time - 15})
        self.assertFalse(self.adaptive_time_limit.check(q).is_ok())
