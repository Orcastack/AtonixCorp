from workspaces.models import WorkspaceGroup
from workspaces.models import Workspace


TASK_TYPE_DEPARTMENT_MAP = {
    'generate_statement': 'Financial Reporting',
    'journal_entry_approval': 'Controllership',
    'approval_journal_entry': 'Controllership',
    'document_request': 'Risk, Audit, and Compliance',
    'equity_transaction_approval': 'Risk, Audit, and Compliance',
    'process_payroll': 'Payroll',
    'run_tax_calculation': 'Tax',
    'import_bank_feed': 'Treasury',
}

DEPARTMENT_COST_CENTER_MAP = {
    'Controllership': 'FIN-CTRL-100',
    'Accounts Payable': 'FIN-AP-110',
    'Accounts Receivable': 'FIN-AR-120',
    'Treasury': 'FIN-TRSY-130',
    'Payroll': 'FIN-PAY-140',
    'Tax': 'FIN-TAX-150',
    'FP&A': 'FIN-FPA-160',
    'Financial Reporting': 'FIN-REP-170',
    'Risk, Audit, and Compliance': 'FIN-RISK-180',
    'Intercompany and Consolidation': 'FIN-CONS-190',
}

KEYWORD_DEPARTMENT_RULES = [
    (('journal', 'ledger', 'close', 'reconciliation', 'controll'), 'Controllership'),
    (('payable', 'vendor', 'bill', 'supplier'), 'Accounts Payable'),
    (('receivable', 'invoice', 'collection', 'customer billing'), 'Accounts Receivable'),
    (('cash', 'treasury', 'bank', 'liquidity', 'payment'), 'Treasury'),
    (('payroll', 'payslip', 'compensation'), 'Payroll'),
    (('tax', 'filing', 'jurisdiction'), 'Tax'),
    (('budget', 'forecast', 'variance', 'fp&a', 'planning'), 'FP&A'),
    (('statement', 'board pack', 'reporting', 'trial balance'), 'Financial Reporting'),
    (('audit', 'compliance', 'approval', 'review', 'risk', 'document'), 'Risk, Audit, and Compliance'),
    (('intercompany', 'consolidation', 'elimination'), 'Intercompany and Consolidation'),
]


def _infer_department_name(payload):
    metadata = payload.get('metadata') or {}
    explicit_name = (
        payload.get('department_name')
        or metadata.get('department_name')
        or metadata.get('department')
    )
    if explicit_name:
        return explicit_name

    task_type = str(payload.get('task_type') or payload.get('type') or '').strip().lower()
    origin_type = str(payload.get('origin_type') or payload.get('source_object_type') or '').strip().lower()
    domain = str(payload.get('domain') or '').strip().lower()
    text = ' '.join(
        part for part in [
            task_type,
            origin_type,
            domain,
            str(payload.get('title') or '').lower(),
            str(payload.get('description') or '').lower(),
        ]
        if part
    )

    if task_type in TASK_TYPE_DEPARTMENT_MAP:
        return TASK_TYPE_DEPARTMENT_MAP[task_type]
    if origin_type in TASK_TYPE_DEPARTMENT_MAP:
        return TASK_TYPE_DEPARTMENT_MAP[origin_type]

    for keywords, department_name in KEYWORD_DEPARTMENT_RULES:
        if any(keyword in text for keyword in keywords):
            return department_name
    return ''


def apply_department_routing(payload):
    metadata = {**(payload.get('metadata') or {})}
    workspace_id = payload.get('workspace_id') or metadata.get('workspace_id')
    entity = payload.get('entity')
    entity_id = payload.get('entity_id') or getattr(entity, 'id', None) or metadata.get('entity_id')
    if not workspace_id and entity_id:
        workspace_id = Workspace.objects.filter(linked_entity_id=entity_id).values_list('id', flat=True).first()
    department_name = _infer_department_name(payload)
    cost_center = (payload.get('cost_center') or metadata.get('cost_center') or '').strip()
    has_explicit_user_assignment = (
        payload.get('assignee_type') == 'user'
        and str(payload.get('assignee_id') or getattr(payload.get('assigned_to'), 'id', '') or '')
    )

    routed_payload = {**payload}
    if department_name:
        metadata['department_name'] = department_name
        if not cost_center:
            cost_center = DEPARTMENT_COST_CENTER_MAP.get(department_name, '')
    if cost_center:
        metadata['cost_center'] = cost_center

    department = None
    if workspace_id:
        departments = WorkspaceGroup.objects.select_related('owner').filter(workspace_id=workspace_id)
        if cost_center:
            department = departments.filter(cost_center=cost_center).first()
        if department is None and department_name:
            department = departments.filter(name=department_name).first()

    if department:
        metadata.update({
            'department_id': str(department.id),
            'department_name': department.name,
            'cost_center': department.cost_center,
            'department_owner_id': str(department.owner_id or ''),
        })
        if department.owner and not has_explicit_user_assignment:
            routed_payload['assignee_type'] = 'user'
            routed_payload['assignee_id'] = str(department.owner_id)
            routed_payload['assigned_to'] = department.owner
        elif not department.owner and not has_explicit_user_assignment:
            routed_payload['assignee_type'] = 'group'
            routed_payload['assignee_id'] = str(department.id)
            routed_payload['assigned_to'] = None

    routed_payload['metadata'] = metadata
    routed_payload['workspace_id'] = workspace_id
    return routed_payload