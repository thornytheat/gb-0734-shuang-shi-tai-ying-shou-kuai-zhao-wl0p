from app.clock import Period, cut_query
from app.modules.m5_backfill.service import compare_opening


def test_backfill_freezes_effective_date(data, period):
    before, after, report = compare_opening(data, period)
    assert before['cut']['effective'] == after['cut']['effective'] == '2025-12-31'
    assert report['totals'] == {'face_cents': 80000, 'receipts_cents': 3025, 'reversed_cents': 18000, 'balance_cents': 58975}


def test_pending_to_applied_uses_original_source_row(data, period):
    _, _, report = compare_opening(data, period)
    evidence = next(row for row in report['changes'] if row['event']['event_id'] == 'B-REV')
    assert (evidence['event']['line'], evidence['before']['code'], evidence['after']['state']) == (3, 'TARGET_PENDING', 'APPLIED')
    assert evidence['after']['target']['event_id'] == 'B-V1'


def test_unrelated_period_receipt_not_in_backfill(data, period):
    _, _, report = compare_opening(data, period)
    seen = {row['event']['event_id'] for row in report['changes']}
    assert 'F-P1' in seen
    assert {'A-P1', 'C-P2', 'E-P1', 'A-OTHER-CUST'}.isdisjoint(seen)


def test_due_only_change_is_evidence_even_without_cash_movement(data):
    pair = Period(cut_query('2025-12-31', '2026-02-02T23:55+08:00'), cut_query('2026-01-31', '2026-02-03T09:00+08:00'))
    _, _, report = compare_opening(data, pair)
    a = next(row for row in report['invoices'] if row['invoice_id'] == 'AR-1001')
    assert a['delta']['balance_cents'] == 0
    assert (a['before']['due'], a['after']['due']) == ('2025-12-20', '2026-01-20')


def test_equal_knowledge_produces_no_backfill(data, period):
    pair = Period(cut_query('2025-12-31', '2026-02-06T04:00:00Z'), period.closing)
    _, _, report = compare_opening(data, pair)
    assert report['changes'] == report['invoices'] == []
    assert set(report['totals'].values()) == {0}


def test_backward_knowledge_has_business_error(client, query):
    response = client.get('/api/backfill', params={**query, 'open_known': '2026-03-01T00:00Z'})
    assert (response.status_code, response.json()['code']) == (422, 'INVALID_PERIOD')
