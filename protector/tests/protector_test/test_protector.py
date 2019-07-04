import unittest

from protector.protector_main import Protector
from protector.query.query import OpenTSDBQuery
from mock import mock

p = None


class MockRedis(object):
    def exists(self, key):
        return False


@mock.patch("redis.Redis", mock.MagicMock(return_value=MockRedis()))
def get_protector():
    global p
    db_conf = {"redis": {"host":"", "port":"", "password":""}}
    p = Protector({"query_no_aggregator": None}, [], db_conf, False)


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

    def test_blacklist(self):

        p.blacklist = ["^releases$", "^mymetric\.", ".*java.*boot.*version.*"]

        self.assertFalse(p.check(OpenTSDBQuery(self.payload1)).is_ok())
        self.assertTrue(p.check(OpenTSDBQuery(self.payload2)).is_ok())
        self.assertTrue(p.check(OpenTSDBQuery(self.payload3)).is_ok())

        p.blacklist = []
        self.assertTrue(p.check(OpenTSDBQuery(self.payload1)).is_ok())

    def test_safe_mode(self):

        p.blacklist = []
        p.safe_mode = True

        self.assertTrue(p.check(OpenTSDBQuery(self.payload4)).is_ok())

        p.safe_mode = False
        self.assertFalse(p.check(OpenTSDBQuery(self.payload4)).is_ok())

    def test_invalid_queries(self):

        p.safe_mode = False

        with self.assertRaisesRegexp(Exception, 'Invalid OpenTSDB query'):
            p.check(OpenTSDBQuery('{}'))

        with self.assertRaisesRegexp(Exception, 'Invalid OpenTSDB query'):
            p.check(OpenTSDBQuery('{"start": ""}'))
