from dataclasses import replace

from app.clock import cut_query
from app.modules.m2_versions.service import versions_at


def test_prior_cut_hides_replacement_and_conflict(data):
    result = versions_at(data, cut_query('2025-12-31', '2025-12-31T23:59+08:00'))
    rows = {row['event_id']: row for row in result['versions']}
    assert rows['A-V1']['state'] == 'ACTIVE'
    assert rows['A-V1']['known_to'] is None
    assert 'A-V2' not in rows and 'B-V1' not in rows
    assert result['quarantine'] == []


def test_knowledge_boundary_retires_parent_at_exact_instant(data):
    previous = versions_at(data, cut_query('2025-12-31', '2026-02-03T08:59:59.999999+08:00'))
    current = versions_at(data, cut_query('2025-12-31', '2026-02-03T01:00Z'))
    assert [row['event_id'] for row in previous['versions'] if row['state'] == 'ACTIVE' and row['invoice_id'] == 'AR-1001'] == ['A-V1']
    a = {row['event_id']: row for row in current['versions'] if row['invoice_id'] == 'AR-1001'}
    assert a['A-V1']['known_to'] == '2026-02-03T01:00:00.000000Z'
    assert (a['A-V1']['replaced_by'], a['A-V2']['state'], a['A-V2']['due']) == ('A-V2', 'ACTIVE', '2026-01-20')


def test_adjacent_intervals_exclusive_end(data, period):
    observed = []
    for day in ['2026-01-19', '2026-01-20']:
        result = versions_at(data, cut_query(day, '2026-02-06T04:00Z'))
        observed.append([row['event_id'] for row in result['versions'] if row['state'] == 'ACTIVE' and row['invoice_id'] == 'AR-1004'])
    assert observed == [['D-V1'], ['D-V2']]  # TRAP-23


def test_overlap_reject_keeps_prior_version(data, period):
    result = versions_at(data, period.closing)
    conflict = next(row for row in result['quarantine'] if row['event']['event_id'] == 'C-OV')
    assert conflict['code'] == 'INTERVAL_OVERLAP'  # TRAP-25
    assert [row['event_id'] for row in conflict['related']] == ['C-V1']
    assert [row['event_id'] for row in result['versions'] if row['invoice_id'] == 'AR-1003'] == ['C-V1']


def test_same_time_fork_is_order_independent(data, period):
    once = versions_at(data, period.closing)
    data.events.reverse()
    twice = versions_at(data, period.closing)
    assert once == twice  # TRAP-19
    assert [row['event']['event_id'] for row in once['quarantine'] if row['code'] == 'VERSION_FORK'] == ['I-V2A', 'I-V2B']
    assert [row['event_id'] for row in once['versions'] if row['invoice_id'] == 'AR-1009'] == ['I-V1']


def test_customer_identifiers_stay_distinct_and_version_cannot_switch(data, period):
    result = versions_at(data, period.closing)
    lookup = {row['invoice_id']: row['customer_id'] for row in result['versions'] if row['state'] == 'ACTIVE'}
    assert (lookup['AR-1001'], lookup['AR-1002']) == ('00017', '17')  # TRAP-08
    assert [row['event']['event_id'] for row in result['quarantine'] if row['code'] == 'CUSTOMER_CONFLICT'] == ['A-OTHER-CUST']


def test_later_id_conflict_retains_first_event(data, period):
    result = versions_at(data, period.closing)
    conflict = next(row for row in result['quarantine'] if row['code'] == 'EVENT_ID_CONFLICT')
    assert conflict['event']['amount_cents'] == 19000
    assert conflict['related'][0]['amount_cents'] == 10000
    earlier = versions_at(data, cut_query('2026-01-31', '2026-01-31T00:00Z'))
    assert not any(row['code'] == 'EVENT_ID_CONFLICT' for row in earlier['quarantine'])


def test_stale_parent_cannot_overwrite_new_revision(data, period):
    newer = next(row for row in data.events if row.event_id == 'A-V2')
    a = replace(newer, event_id='A-STALE', line=90, known=period.closing.known)
    data.events.append(a)
    result = versions_at(data, period.closing)
    rejected = next(row for row in result['quarantine'] if row['event']['event_id'] == 'A-STALE')
    assert rejected['code'] == 'VERSION_PARENT'  # TRAP-26
    assert [row['event_id'] for row in result['versions'] if row['invoice_id'] == 'AR-1001' and row['state'] == 'ACTIVE'] == ['A-V2']
