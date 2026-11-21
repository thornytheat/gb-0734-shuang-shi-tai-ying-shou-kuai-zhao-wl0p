from app.config import MAX_BYTES
from app.modules.m1_intake.reader import read
from app.modules.m1_intake.contract import COLUMNS


def test_source_counts_conserve(client):
    response = client.get('/api/intake/sample')
    assert response.status_code == 200
    counts = response.json()['counts']
    assert counts == {'input': 43, 'accepted': 32, 'quarantine': 8, 'duplicates': 1, 'blank': 1, 'repeated_headers': 1}
    assert counts['input'] == sum(value for key, value in counts.items() if key != 'input')  # TRAP-04


def test_bom_preserves_first_column(data):
    assert data.encoding == 'utf-8-sig'  # TRAP-02
    assert data.events[0].event_id == 'D-V2'


def test_multiline_preserves_source_positions(data):
    a = next(item for item in data.events if item.event_id == 'A-V1')
    p = next(item for item in data.events if item.event_id == 'A-P1')
    assert (a.line, a.note, p.line) == (4, '华东仓配\n补充交接备注', 6)  # TRAP-03


def test_gb18030_actual_sample(client, branch_raw):
    response = client.post('/api/intake', files={'file': ('branch.csv', branch_raw)})
    assert response.status_code == 200
    body = response.json()
    assert body['encoding'] == 'gb18030' and body['counts']['accepted'] == 2  # TRAP-01
    query = {'source_id': body['source_id'], 'effective': '2026-01-31', 'known': '2026-01-31T22:00+08:00'}
    version = client.get('/api/snapshot', params=query).json()['invoices'][0]['version']
    assert (version['note'], version['customer_id']) == ('分部报送', '00088')


def test_bad_width_isolated_with_source(data):
    row = next(item for item in data.quarantine if item['code'] == 'ROW_WIDTH')
    assert (row['line'], row['raw']) == (35, ['BAD-WIDTH', 'AR-1011', '01312'])  # TRAP-05


def test_money_normalization_and_blank_isolation(data):
    amounts = {item.event_id: item.cents for item in data.events}
    assert (amounts['A-V1'], amounts['C-V1']) == (125050, 170010)  # TRAP-06
    row = next(item for item in data.quarantine if item['code'] == 'AMOUNT_MISSING')
    assert row['raw']['amount_cny'] == 'N/A' and 'J-BAD' not in amounts  # TRAP-07
    assert {row['raw']['amount_cny'] for row in data.quarantine if row['code'] == 'INVALID_AMOUNT'} == {'45.999', '12,05'}


def test_duplicate_comparison_uses_utc(data):
    assert [row['event_id'] for row in data.duplicates] == ['I-V1']  # TRAP-11
    assert sum(item.event_id == 'I-V1' for item in data.events) == 1


def test_conflicting_same_key_isolated_together(data):
    rows = [row for row in data.quarantine if row['event_id'] == 'Z-CON']
    assert [row['line'] for row in rows] == [39, 40]  # TRAP-14
    assert all(row['code'] == 'EVENT_ID_CONFLICT' for row in rows)
    assert all(item.event_id != 'Z-CON' for item in data.events)


def test_zero_and_blanks_and_header_only_have_distinct_errors(client, make_csv):
    contents = [b'', b'\n \n', make_csv()]
    replies = [client.post('/api/intake', files={'file': ('bad.csv', content)}) for content in contents]
    assert [reply.status_code for reply in replies] == [422, 422, 422]
    assert [reply.json()['code'] for reply in replies] == ['EMPTY_FILE', 'BLANK_FILE', 'NO_RECORDS']  # TRAP-18


def test_truncated_quote_fails_without_storing_source(client, make_csv):
    content = make_csv() + b'"unterminated'
    response = client.post('/api/intake', files={'file': ('broken.csv', content)})
    assert response.status_code == 422
    assert response.json() == {'code': 'MALFORMED_CSV', 'message': '第 2 行 CSV 记录损坏'}  # TRAP-16
    with client.app.state.store.connect() as connection:
        assert connection.execute('SELECT count(*) FROM sources').fetchone()[0] == 1


def test_reordered_header_maps_fields(make_csv):
    original = ['A', 'I', '00010', 'VERSION', '2025-01-01', '', '2025-01-05T00:00Z', '2025-02-01', '12.10', '', '备注']
    result = read(make_csv(list(reversed(original)), header=tuple(reversed(COLUMNS))))
    assert [(item.customer_id, item.cents, item.note) for item in result.events] == [('00010', 1210, '备注')]


def test_oversize_upload_is_rejected(client):
    reply = client.post('/api/intake', files={'file': ('big.csv', b'1' * (MAX_BYTES + 1))})
    assert (reply.status_code, reply.json()['code']) == (413, 'FILE_TOO_LARGE')
