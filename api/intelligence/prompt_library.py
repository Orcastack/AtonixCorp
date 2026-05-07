import json


PROMPT_LIBRARY = {
    'tax_treatment_explanation': {
        'version': '2026-04-09.hybrid.v1',
        'system': (
            'You are Claude, an AI assistant helping with tax and equity management for Ledgora. '
            'You must follow explicit tax rules, workspace preferences, and prior confirmed decisions. '
            'You must explain your reasoning, cite references, and never invent rules. '
            'You are not the final authority for tax calculations. Deterministic engine results override narrative reasoning. '
            'If uncertain, say so clearly and recommend human review.'
        ),
    },
}


def build_tax_treatment_prompt(*, model_name, workspace_summary, global_context, workspace_context, deterministic_assessment, request_payload):
    template = PROMPT_LIBRARY['tax_treatment_explanation']
    user_payload = {
        'intent': 'tax_treatment_explanation',
        'requested_model': model_name,
        'workspace_summary': workspace_summary,
        'global_context': global_context,
        'workspace_context': workspace_context,
        'deterministic_assessment': deterministic_assessment,
        'request': request_payload,
        'response_contract': {
            'answer': 'short natural language explanation',
            'proposed_treatment': {'category': 'string', 'rationale': 'string'},
            'references': [{'type': 'global_rule|workspace_precedent|deterministic_rule', 'source': 'string', 'snippet': 'string'}],
            'confidence': 'low|medium|high',
            'requires_human_review': 'boolean',
        },
    }
    return {
        'version': template['version'],
        'system': template['system'],
        'user': json.dumps(user_payload, indent=2, sort_keys=True),
    }
