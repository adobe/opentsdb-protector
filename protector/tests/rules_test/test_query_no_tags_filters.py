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

from protector.rules import query_no_tags_filters
from protector.query.query import OpenTSDBQuery


class TestQueryNoTagsFilters(unittest.TestCase):

    def setUp(self):

        self.query_no_tags_filters = query_no_tags_filters.RuleChecker()

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
                              "tags": {
                                "percentile": "wildcard(*)",
                                "task": "literal_or(Source)"
                              },                              
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
                              "downsample": "20s-max"
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
                              "filters": [],
                              "tags": {}
                            }
                          ]
                        }
                        """

    def test_no_tags(self):

        q = OpenTSDBQuery(self.payload1)
        self.assertTrue(self.query_no_tags_filters.check(q).is_ok())

    def test_no_filters(self):

        q = OpenTSDBQuery(self.payload2)
        self.assertTrue(self.query_no_tags_filters.check(q).is_ok())

    def test_both(self):

        q = OpenTSDBQuery(self.payload3)
        self.assertFalse(self.query_no_tags_filters.check(q).is_ok())

        q = OpenTSDBQuery(self.payload4)
        self.assertFalse(self.query_no_tags_filters.check(q).is_ok())
