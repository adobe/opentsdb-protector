import unittest
from protector.guard.guard import Guard
from protector.query.query import OpenTSDBQuery
from protector.config import default_config


class TestGuard(unittest.TestCase):
    def setUp(self):
        self.config = default_config.DEFAULT_CONFIG
        self.payload = """
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

    def test_guard(self):
        # Test rules loading
        guard = Guard(self.config['rules'])
        q = OpenTSDBQuery(self.payload)
        self.assertTrue(guard.is_allowed(q))
