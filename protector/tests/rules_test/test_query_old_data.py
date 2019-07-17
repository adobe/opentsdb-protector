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

from protector.rules import query_old_data
from protector.query.query import OpenTSDBQuery


class TestQueryOldData(unittest.TestCase):

    def setUp(self):

        self.query_old_data = query_old_data.RuleChecker(90)

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

    def test_old_absolute(self):

        self.assertFalse(self.query_old_data.check(OpenTSDBQuery(self.payload1)).is_ok())

    def test_old_relative(self):

        self.assertFalse(self.query_old_data.check(OpenTSDBQuery(self.payload2)).is_ok())
        self.assertFalse(self.query_old_data.check(OpenTSDBQuery(self.payload3)).is_ok())

        self.assertTrue(self.query_old_data.check(OpenTSDBQuery(self.payload4)).is_ok())
