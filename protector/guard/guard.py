#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

from result import Ok, Err
from protector.rules.loader import import_rules


class Guard(object):
    """
    The guard checks a given query for their possible impact.
    It does so by iterating over all active rules and checking for violations
    """

    def __init__(self, rule_names):
        self.rules = import_rules(rule_names)

    def is_allowed(self, query):

        for name, rule in self.rules.items():
            check = rule.check(query)
            if not check.is_ok():
                return Err({"rule": name, "msg": check.value})
        return Ok(True)
