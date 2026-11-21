from app.modules.m6_bridge.service import period_book


def test_period_equation_independently_reproduces_closing(data, period):
    bridge = period_book(data, period)['bridge']
    assert 313180 + 145000 - 90115 - 28000 == 340065
    assert bridge['status'] == 'MATCHED'
    assert bridge['totals'] == {'opening_cents': 313180, 'posted_cents': 145000, 'collected_cents': 90115,
                                'reversed_cents': 28000, 'closing_cents': 340065, 'expected_cents': 340065, 'difference_cents': 0}


def test_bucket_bridge_each_bucket_conserves_and_migration_nets_to_zero(data, period):
    bridge = period_book(data, period)['bridge']
    assert sum(row['migration_cents'] for row in bridge['buckets']) == 0
    for row in bridge['buckets']:
        assert row['opening_cents'] + row['late_cents'] + row['migration_cents'] + row['period_cents'] == row['closing_cents']
    assert sum(row['closing_cents'] for row in bridge['buckets']) == 340065


def test_bridge_splits_late_from_in_period_gross_movements(data, period):
    bridge = period_book(data, period)['bridge']
    assert bridge['late'] == {'posted_cents': 80000, 'collected_cents': 3025, 'reversed_cents': 18000}
    assert bridge['in_period'] == {'posted_cents': 65000, 'collected_cents': 87090, 'reversed_cents': 10000}
    assert sum(row['late_cents'] for row in bridge['buckets']) == 58975
    assert sum(row['period_cents'] for row in bridge['buckets']) == -32090


def test_migration_uses_restated_balance_before_current_receipt(data, period):
    bridge = period_book(data, period)['bridge']
    row = next(row for row in bridge['invoices'] if row['invoice_id'] == 'AR-1003')
    assert row['bucket_path'] == {'opening': 'd31_60', 'restated': 'd31_60', 'aged_to': 'd61_90', 'closing': 'd61_90'}
    assert row['restated']['balance_cents'] == 120000 and row['closing']['balance_cents'] == 90000
    band = next(row for row in bridge['buckets'] if row['bucket'] == 'd61_90')
    assert (band['migration_cents'], band['period_cents']) == (120000, -30000)


def test_bridge_requires_distinct_period_days(client, query):
    reply = client.get('/api/bridge', params={**query, 'open_effective': query['effective']})
    assert (reply.status_code, reply.json()['code']) == (422, 'INVALID_PERIOD')


def test_bridge_api_matches_each_aging_bucket(client, query):
    bridge = client.get('/api/bridge', params=query).json()
    aged = client.get('/api/aging', params=query).json()
    assert {row['bucket']: row['closing_cents'] for row in bridge['buckets']} == {row['bucket']: row['balance_cents'] for row in aged['buckets']}
    assert all(row['reconciliation']['difference_cents'] == 0 for row in bridge['invoices'])
