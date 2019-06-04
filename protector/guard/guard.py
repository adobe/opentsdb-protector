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
        if not query:
            return Err("Empty query !?")

        for rule in self.rules.values():
            check = rule.check(query)
            if not check.is_ok():
                return Err(check.value)
        return Ok(True)
