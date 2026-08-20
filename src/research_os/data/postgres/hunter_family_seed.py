"""Canonical seed rows for the HunterFamily registry."""

SEED_FAMILIES = [
    {
        "family_id": "hf-object-authz",
        "name": "OBJECT_AUTHORIZATION",
        "target_node_kinds": ["HTTP_OPERATION", "RESOURCE_INSTANCE_CANDIDATE"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Object authorization boundary on {origin}{path} "
            "may allow cross-owner access to {resource_id}."
        ),
        "evidence_requirements": {
            "required_observation_kinds": ["HTTP_AUTHORIZATION_DIFFERENTIAL"],
        },
        "validation_tier": "V3",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-workflow-trans",
        "name": "WORKFLOW_STATE_TRANSITION",
        "target_node_kinds": ["WORKFLOW_TRANSITION"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Workflow transition {transition} on {resource_id} at {origin}{path} "
            "may lack authorization check."
        ),
        "evidence_requirements": {
            "required_observation_kinds": ["HTTP_STATE_TRANSITION_AUTHORIZATION"],
        },
        "validation_tier": "V3",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-exposed-api-spec",
        "name": "EXPOSED_API_SPEC",
        "target_node_kinds": ["API_SPEC"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "API specification at {canonical_key} documents endpoint surface "
            "that may be wider than observed access controls."
        ),
        "evidence_requirements": {
            "required_fact_kinds": ["API_SPEC"],
        },
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-unprotected-hostname",
        "name": "UNPROTECTED_HOSTNAME",
        "target_node_kinds": ["HOSTNAME"],
        "preconditions": {
            "scope_classification": "IN_SCOPE",
            "absent_edge_kind": "OBSERVED_UNDER",
        },
        "claim_template": (
            "Hostname {canonical_key} is in scope but has no observed "
            "active probe coverage yet."
        ),
        "evidence_requirements": {"required_edge_kind": "OBSERVED_UNDER"},
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
    {
        "family_id": "hf-tech-cve-surface",
        "name": "TECH_KNOWN_CVE_SURFACE",
        "target_node_kinds": ["TECH"],
        "preconditions": {"scope_classification": "IN_SCOPE"},
        "claim_template": (
            "Technology {technology} at {canonical_key} is a candidate "
            "for known-vulnerability class verification."
        ),
        "evidence_requirements": {"required_fact_kinds": ["TECH"]},
        "validation_tier": "V2",
        "enabled": True,
        "version": 1,
    },
]
