import unittest

from protector.rules import exceed_time_limit
from protector.query.query import OpenTSDBQuery


class TestQueryExceedFrequency(unittest.TestCase):

    def setUp(self):

        self.exceed_time_limit = exceed_time_limit.RuleChecker(20)

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

        q = OpenTSDBQuery(self.payload1)
        q.set_stats({'duration': 1.5})

        self.assertTrue(self.exceed_time_limit.check(q).is_ok())

    def test_above(self):

        q = OpenTSDBQuery(self.payload2)
        q.set_stats({'duration': 20})

        self.assertFalse(self.exceed_time_limit.check(q).is_ok())

    def test_none(self):

        q = OpenTSDBQuery(self.payload3)

        self.assertTrue(self.exceed_time_limit.check(q).is_ok())
