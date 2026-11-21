from concurrent.futures import ThreadPoolExecutor

from app.evidence import canonical, digest


def test_rerun_recomputes_same_manifest_and_export(client, query):
    first = client.post('/api/archive', json=query).json()
    run = first['manifest']['run_id']
    before = client.get(f'/api/archive/{run}/export')
    resp = client.post(f'/api/archive/{run}/rerun')
    assert resp.status_code == 200 and first['created'] is True
    assert resp.json()['created'] is False and resp.json()['manifest'] == first['manifest']
    assert before.content == client.get(f'/api/archive/{run}/export').content
    assert client.get('/api/archive').json()['runs'] == [first['manifest']]


def test_equivalent_utc_params_do_not_duplicate_run(client, query):
    first = client.post('/api/archive', json=query).json()
    second = client.post('/api/archive', json={**query, 'known': '2026-02-06T04:00Z'}).json()
    assert first['manifest'] == second['manifest'] and not second['created']


def test_distinct_cut_has_distinct_archive_key(client, query):
    first = client.post('/api/archive', json=query).json()
    second = client.post('/api/archive', json={**query, 'effective': '2026-01-30'}).json()
    assert first['manifest']['run_id'] != second['manifest']['run_id']
    assert len(client.get('/api/archive').json()['runs']) == 2


def test_sqlite_write_failure_rollback_then_retry(client, query):
    store = client.app.state.store
    with store.connect() as connection:
        connection.execute("CREATE TRIGGER fail_archive AFTER INSERT ON archives BEGIN SELECT RAISE(ABORT, 'test'); END")
    failure = client.post('/api/archive', json=query)
    assert (failure.status_code, failure.json()['code']) == (503, 'ARCHIVE_WRITE_FAILED')
    assert client.get('/api/archive').json()['runs'] == []
    with store.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM sources').fetchone()[0] == 1
        connection.execute('DROP TRIGGER fail_archive')
    assert client.post('/api/archive', json=query).json()['created'] is True


def test_concurrent_writes_leave_one_committed_archive(client, query):
    with ThreadPoolExecutor(max_workers=4) as pool:
        replies = list(pool.map(lambda _: client.post('/api/archive', json=query), range(4)))
    assert [reply.status_code for reply in replies] == [200] * 4
    runs = [reply.json() for reply in replies]
    assert sum(run['created'] for run in runs) == 1
    assert len({run['manifest']['run_id'] for run in runs}) == 1
    assert len(client.get('/api/archive').json()['runs']) == 1


def test_evidence_contains_digest_row_and_cut(client, query, raw):
    manifest = client.post('/api/archive', json=query).json()['manifest']
    reply = client.get(f"/api/archive/{manifest['run_id']}/export")
    assert reply.headers['content-disposition'] == f"attachment; filename=\"receivable-{manifest['run_id'][:12]}.json\""
    body = reply.json()
    assert body['manifest']['source_id'] == digest(raw)
    assert body['manifest']['result_digest'] == digest(canonical(body['result']))
    assert body['result']['closing']['cut']['known'] == '2026-02-06T04:00:00.000000Z'
    assert body['result']['intake']['quarantine'][0]['line'] == 30
    assert body['result']['bridge']['totals']['closing_cents'] == 340065


def test_tampering_rejects_export_and_rerun_without_overwrite(client, query):
    archive = client.post('/api/archive', json=query).json()
    run = archive['manifest']['run_id']
    with client.app.state.store.connect() as connection:
        connection.execute('UPDATE archives SET result_digest=? WHERE run_id=?', ('bad-digest', run))
    actions = [client.get(f'/api/archive/{run}/export'), client.post(f'/api/archive/{run}/rerun')]
    assert [(reply.status_code, reply.json()['code']) for reply in actions] == [(409, 'ARCHIVE_MISMATCH')] * 2
    assert client.get('/api/archive').json()['runs'][0]['result_digest'] == 'bad-digest'


def test_missing_archive_and_source_have_distinct_codes(client, query):
    source = client.post('/api/archive', json={**query, 'source_id': 'missing'})
    run = client.post('/api/archive/missing/rerun')
    assert [(reply.status_code, reply.json()['code']) for reply in (source, run)] == [(404, 'SOURCE_NOT_FOUND'), (404, 'RUN_NOT_FOUND')]
