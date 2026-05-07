from django.core.management.base import BaseCommand

from intelligence.models import GlobalKnowledgeChunk, GlobalKnowledgeDocument


SEED_DOCUMENTS = [
    {
        'title': 'ZA Corporate Income Tax Baseline',
        'source_type': 'internal_seed',
        'source': 'South Africa corporate tax baseline seed',
        'jurisdiction': 'ZA',
        'topic': 'tax',
        'content': (
            'South African corporate income tax generally applies to taxable income of resident companies. '
            'Routine operating expenses are typically deductible when incurred in the production of income, '
            'while capital expenditure usually requires capitalization or separate allowance treatment.'
        ),
        'metadata': {
            'references': ['South African Income Tax Act', 'Ledgora Phase 1 ZA expense treatment baseline'],
            'effective_period': '2025+',
        },
        'chunks': [
            'Resident companies in South Africa are generally taxed on taxable income and the Phase 1 deterministic baseline uses a 27 percent corporate rate unless workspace tax profile rules override it.',
            'Ordinary operating expenses linked to producing income are treated as potentially deductible, but capital assets, equipment, and other capital items should not be immediately deducted without capitalization review.',
            'If the transaction is an equity event, multi-jurisdiction restructuring item, or otherwise ambiguous, the AI layer should defer to human review and treat the deterministic engine as non-final.',
        ],
    },
    {
        'title': 'US Corporate Tax Baseline',
        'source_type': 'internal_seed',
        'source': 'United States corporate tax baseline seed',
        'jurisdiction': 'US',
        'topic': 'tax',
        'content': (
            'US federal corporate income tax applies to taxable corporate income. '
            'Ordinary and necessary business expenses are generally deductible, subject to capitalization, '
            'timing, and limitation rules.'
        ),
        'metadata': {
            'references': ['IRC Section 162', 'Ledgora US baseline'],
            'effective_period': '2025+',
        },
        'chunks': [
            'The Phase 1 US corporate baseline uses a 21 percent rate unless explicit tax profile rules are configured for the entity and jurisdiction.',
            'Operating costs that are ordinary and necessary may be deductible, but capital improvements, fixed assets, and similar long-lived items should be capitalized or handled through separate schedules.',
            'Narrative AI explanations must not claim to provide legal or tax advice and must surface uncertainty when facts are incomplete.',
        ],
    },
    {
        'title': 'UK Corporation Tax Baseline',
        'source_type': 'internal_seed',
        'source': 'United Kingdom corporation tax baseline seed',
        'jurisdiction': 'UK',
        'topic': 'tax',
        'content': (
            'UK corporation tax generally applies to company profits, with ordinary revenue expenses potentially '
            'deductible and capital items requiring capital allowance analysis or separate treatment.'
        ),
        'metadata': {
            'references': ['HMRC corporation tax guidance', 'Ledgora UK baseline'],
            'effective_period': '2025+',
        },
        'chunks': [
            'The Phase 1 UK corporate baseline uses a 25 percent corporation tax rate unless a workspace or entity tax profile provides an override.',
            'Revenue expenses may be deductible, but capital expenditure should be escalated for capital allowance or deferred treatment review instead of immediate deduction.',
            'Cross-border, financing, and equity-related matters require heightened review and should not be finalized purely from model reasoning.',
        ],
    },
    {
        'title': 'Global Hybrid AI Governance Baseline',
        'source_type': 'internal_seed',
        'source': 'Ledgora hybrid AI governance baseline',
        'jurisdiction': 'GLOBAL',
        'topic': 'tax',
        'content': (
            'Claude is the reasoning layer, not the final calculator. Deterministic tax engines, audit logs, '
            'workspace isolation, and traceable references are mandatory in the Ledgora hybrid AI design.'
        ),
        'metadata': {
            'references': ['Hybrid Claude Integration Directive'],
            'effective_period': '2026-04-09+',
        },
        'chunks': [
            'Global knowledge must not contain client-specific data and should only store public or platform-wide rules, policies, and regulatory baselines.',
            'Workspace knowledge must always be filtered by workspace identifier and should be built from confirmed decisions, overrides, preferences, and approved documents.',
            'AI outputs must be auditable: store request context, response context, tools used, deterministic trace, and final user feedback outcome for each interaction.',
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed global AI knowledge documents and chunks for the hybrid AI tax layer.'

    def handle(self, *args, **options):
        created_documents = 0
        created_chunks = 0

        for seed in SEED_DOCUMENTS:
            document, doc_created = GlobalKnowledgeDocument.objects.update_or_create(
                source=seed['source'],
                jurisdiction=seed['jurisdiction'],
                topic=seed['topic'],
                defaults={
                    'title': seed['title'],
                    'source_type': seed['source_type'],
                    'content': seed['content'],
                    'metadata': seed['metadata'],
                    'is_active': True,
                },
            )
            if doc_created:
                created_documents += 1

            existing_indexes = set(document.chunks.values_list('chunk_index', flat=True))
            for chunk_index, text in enumerate(seed['chunks']):
                _, chunk_created = GlobalKnowledgeChunk.objects.update_or_create(
                    document=document,
                    chunk_index=chunk_index,
                    defaults={
                        'text': text,
                        'jurisdiction': seed['jurisdiction'],
                        'topic': seed['topic'],
                        'source': seed['source'],
                        'effective_date': None,
                        'metadata': seed['metadata'],
                    },
                )
                if chunk_created or chunk_index not in existing_indexes:
                    created_chunks += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded global AI knowledge. Documents created: {created_documents}. Chunks created or refreshed: {created_chunks}.'
            )
        )