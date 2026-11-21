from app.clock import cut_query
from app.modules.m3_snapshot.service import snapshot
from app.modules.m4_aging.buckets import bucket
from app.modules.m4_aging.service import age


def test_day_zero_is_current_and_day_one_overdue():
    assert [bucket(day) for day in (-1, 0, 1)] == ['current', 'current', 'd01_30']


def test_bucket_thresholds_are_inclusive_at_upper_end():
    assert [bucket(day) for day in (30, 31, 60, 61, 90, 91)] == ['d01_30', 'd31_60', 'd31_60', 'd61_90', 'd61_90', 'd91_plus']


def test_due_date_restated_without_advancing_effective_day(data):
    before = age(snapshot(data, cut_query('2025-12-31', '2025-12-31T23:59+08:00')))
    after = age(snapshot(data, cut_query('2025-12-31', '2026-02-06T04:00Z')))
    look = lambda report: next(row for row in report['invoices'] if row['invoice_id'] == 'AR-1001')
    assert (look(before)['bucket'], look(before)['days_overdue']) == ('d01_30', 11)
    assert (look(after)['bucket'], look(after)['days_overdue']) == ('current', 0)


def test_cleared_invoices_are_not_bucketed(data, period):
    report = age(snapshot(data, period.closing))
    assert report['cleared'] == 1
    assert 'AR-1005' not in {row['invoice_id'] for row in report['invoices']}
    assert sum(row['count'] for row in report['buckets']) == 7


def test_cross_year_bucket_totals_and_overdue(client, query):
    report = client.get('/api/aging', params=query).json()
    assert [row['balance_cents'] for row in report['buckets']] == [50000, 110025, 60040, 90000, 30000]
    assert (report['total_cents'], report['overdue_cents'], report['difference_cents']) == (340065, 290065, 0)


def test_aging_returns_zero_buckets_when_cut_precedes_data(data):
    report = age(snapshot(data, cut_query('2025-01-01', '2025-12-31T23:59+08:00')))
    assert len(report['buckets']) == 5 and all(row['balance_cents'] == row['count'] == 0 for row in report['buckets'])
    assert report['invoices'] == [] and report['difference_cents'] == 0
