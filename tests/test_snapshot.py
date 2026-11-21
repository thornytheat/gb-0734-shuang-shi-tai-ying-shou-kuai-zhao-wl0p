from app.clock import cut_query
from app.modules.m3_snapshot.service import snapshot


def invoice(result, key):
    return next(row for row in result['invoices'] if row['invoice_id'] == key)


def test_snapshot_holds_business_date_and_knowledge_independent(data):
    opening = snapshot(data, cut_query('2025-12-31', '2025-12-31T23:59+08:00'))
    revisited = snapshot(data, cut_query('2025-12-31', '2026-02-06T12:00+08:00'))
    closing = snapshot(data, cut_query('2026-01-31', '2026-02-06T12:00+08:00'))
    assert [x['totals']['balance_cents'] for x in (opening, revisited, closing)] == [313180, 372155, 340065]
    assert invoice(opening, 'AR-1001')['due'] == '2025-12-20'
    assert invoice(revisited, 'AR-1001')['due'] == '2026-01-20'
    assert 'AR-1007' not in {row['invoice_id'] for row in closing['invoices']}


def test_reversal_arrives_before_invoice(data):
    early = snapshot(data, cut_query('2025-12-31', '2026-01-03T09:59:59+08:00'))
    exact = snapshot(data, cut_query('2025-12-31', '2026-01-03T10:00+08:00'))
    assert [(row['event']['event_id'], row['code'], row['target']) for row in early['pending']] == [('B-REV', 'TARGET_PENDING', None)]  # TRAP-13
    assert exact['pending'] == []
    row = invoice(exact, 'AR-1002')
    assert row['balance_cents'] == 72000 and row['movements'][0]['target']['event_id'] == 'B-V1'


def test_late_reversal_targets_historical_version(data, period):
    result = snapshot(data, period.closing)
    a = invoice(result, 'AR-1001')
    reversal = next(row for row in a['movements'] if row['event']['kind'] == 'REVERSAL')
    assert (a['version']['event_id'], reversal['target']['event_id'], a['reversed_cents']) == ('A-V2', 'A-V1', 10000)
    assert reversal['at_event']['event_id'] == 'A-V2'


def test_cutoff_includes_exact_offset_equivalent_and_excludes_one_second_later(data, period):
    equal = snapshot(data, period.closing)
    later = snapshot(data, cut_query('2026-01-31', '2026-02-06T04:00:01Z'))
    assert invoice(equal, 'AR-1005')['balance_cents'] == 0
    assert all(row['event']['event_id'] != 'E-P2' for row in equal['quarantine'])
    assert next(row for row in later['quarantine'] if row['event']['event_id'] == 'E-P2')['code'] == 'EXCEEDS_BALANCE'


def test_overpayment_wholly_quarantined(data, period):
    result = snapshot(data, period.closing)
    bad = next(row for row in result['quarantine'] if row['event']['event_id'] == 'H-P1')
    assert (bad['code'], bad['available_cents']) == ('EXCEEDS_BALANCE', 10040)
    assert invoice(result, 'AR-1008')['balance_cents'] == 10040


def test_wrong_customer_and_wrong_event_kind_are_separate(data, period):
    result = snapshot(data, period.closing)
    reasons = {row['event']['event_id']: row['code'] for row in result['quarantine']}
    assert (reasons['D-X'], reasons['C-INVALID']) == ('TARGET_SCOPE', 'TARGET_INVALID')
    assert invoice(result, 'AR-1004')['reversed_cents'] == 0


def test_snapshot_api_requires_explicit_timezone_and_real_date(client, query):
    bad_time = client.get('/api/snapshot', params={**query, 'known': '2026-02-06T12:00'})
    bad_date = client.get('/api/snapshot', params={**query, 'effective': '2026-02-30'})
    assert [(reply.status_code, reply.json()['code']) for reply in (bad_time, bad_date)] == [(422, 'INVALID_CUT')] * 2


def test_cent_sums_no_binary_float_error(data, period):
    result = snapshot(data, period.closing)
    assert result['totals'] == {'face_cents': 508190, 'receipts_cents': 140125, 'reversed_cents': 28000, 'balance_cents': 340065}  # TRAP-10
    assert invoice(result, 'AR-1003')['face_cents'] - invoice(result, 'AR-1003')['receipts_cents'] == 100000
