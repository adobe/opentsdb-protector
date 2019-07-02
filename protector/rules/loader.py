import logging
import importlib


def import_rules(rule_names):
    rules = {}
    for rule_name, rule_param in rule_names.items():
        try:
            rule_module = import_rule("protector.rules.{}".format(rule_name))
            if rule_param is None:
                rules[rule_name] = rule_module.RuleChecker()
            else:
                rules[rule_name] = rule_module.RuleChecker(rule_param)
        except Exception as e:
            logging.error("Could not load rule: %s. Error: %s", rule_name, e.message)
    return rules


def import_rule(path):
    """
    Load the given rule
    :param path: Import path to rule
    """
    rule = importlib.import_module(path)
    return rule
