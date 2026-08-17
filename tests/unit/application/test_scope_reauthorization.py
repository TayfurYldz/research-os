from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.scope_reauthorization import reevaluate_redirect_location
from research_os.core.enums import ReasonCode, ScopeDecision, ScopeRuleEffect
from research_os.core.scope_compiler import ScopeRuleDefinition, compile_scope_rules


class RedirectReauthorizationTests(unittest.TestCase):
    def test_redirect_location_requires_fresh_core_evaluation(self) -> None:
        compiled = compile_scope_rules(
            (
                ScopeRuleDefinition(
                    rule_id="rule-allow",
                    effect=ScopeRuleEffect.ALLOW,
                    scheme="https",
                    host="example.com",
                    port=None,
                    path_prefix=None,
                    source_reference="scope-src",
                ),
            )
        )
        allowed = reevaluate_redirect_location("https://example.com/next", compiled)
        self.assertEqual(allowed.decision, ScopeDecision.ALLOW)
        denied = reevaluate_redirect_location("https://evil.example/next", compiled)
        self.assertEqual(denied.decision, ScopeDecision.DENY)
        self.assertEqual(denied.reason_code, ReasonCode.SCOPE_NOT_EXPLICITLY_ALLOWED)


if __name__ == "__main__":
    unittest.main()
