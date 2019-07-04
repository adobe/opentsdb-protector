import unittest

from protector.rules import too_many_datapoints
from protector.query.query import OpenTSDBQuery


class TestQueryTooManyDatapoints(unittest.TestCase):

    def setUp(self):

        self.too_many_datapoints = too_many_datapoints.RuleChecker(10000)

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

    def test_too_many(self):

        q = OpenTSDBQuery(self.payload1)
        q.set_stats({'emittedDPs': 10001})

        self.assertFalse(self.too_many_datapoints.check(q).is_ok())

    def test_less(self):

        q = OpenTSDBQuery(self.payload2)
        q.set_stats({'emittedDPs': 999})

        self.assertTrue(self.too_many_datapoints.check(q).is_ok())

    def test_none(self):

        q = OpenTSDBQuery(self.payload3)

        self.assertTrue(self.too_many_datapoints.check(q).is_ok())
