"""Transactional labels, immutable revision history, and coordinate validation."""
import copy
from contextlib import contextmanager, closing
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time

SCHEMA = 'forest-bird-input-manual-v1'
ID = re.compile(r'^fb_\d{4,}$')
PARTS = ('bird', 'head', 'eye')
VISIBILITY = {'visible', 'partial', 'hidden', 'out_of_frame', 'unknown'}
TARGETS = {'eye', 'head', 'body', 'none', 'unknown'}
STATUSES = {'pending', 'draft', 'annotated', 'reviewed', 'needs_adjudication'}


class Problem(Exception):
    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.status, self.details = status, details


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def actor(value):
    if not isinstance(value, dict):
        raise Problem('actor must contain id and kind')
    ident, kind = value.get('id', ''), value.get('kind')
    if not isinstance(ident, str) or not re.fullmatch(r'[\w. @-]{1,80}', ident):
        raise Problem('actor.id must be 1-80 letters, digits, spaces, . @ - or _')
    if kind not in ('human', 'ai'):
        raise Problem('actor.kind must be human or ai')
    if not ident.strip():
        raise Problem('actor.id cannot be blank')
    return {'id': ident.strip(), 'kind': kind}


def initial(meta):
    return {'schema_version': SCHEMA, 'image_id': meta['image_id'],
            'annotation_image': {'sha256': meta['png_sha256'], 'input_chw_u8_sha256': meta['input_sha256'],
                                 'width': 384, 'height': 256, 'coordinate_space': 'z8_input_384x256',
                                 'preprocess_id': meta['preprocess_id']},
            'annotation_status': 'pending', 'presence': None, 'instances': None,
            'uncertain_regions': None, 'review_decision': 'unassessed', 'notes': '',
            'reference_consulted': False, 'split': None, 'review': None, 'provenance': None,
            'id_counters': {'bird': 1, 'uncertain': 1}}


def validate(value, meta):
    """Reject invalid geometry even in drafts; require completeness on submission."""
    if not isinstance(value, dict):
        raise Problem('annotation must be an object')
    v = copy.deepcopy(value)
    frozen = initial(meta)
    for key in ('schema_version', 'image_id', 'annotation_image'):
        if v.get(key) != frozen[key]:
            raise Problem(f'{key} does not match this frozen input image')
    if v.get('split') is not None:
        raise Problem('Dataset split is not assigned by the annotation tool')
    status = v.get('annotation_status')
    if status not in STATUSES:
        raise Problem('Invalid annotation_status')
    if v.get('presence') not in (None, 'present', 'absent', 'uncertain'):
        raise Problem('Invalid presence')
    if v.get('review_decision') not in ('unassessed', 'reasonable', 'error', 'uncertain'):
        raise Problem('Invalid review_decision')
    if not isinstance(v.get('reference_consulted'), bool):
        raise Problem('reference_consulted must be boolean')
    if not isinstance(v.get('notes', ''), str) or len(v.get('notes', '')) > 10000:
        raise Problem('Notes must be text, at most 10000 characters')
    issues = []

    def point(p, label, optional=True):
        if p is None and optional:
            return
        if (not isinstance(p, list) or len(p) != 2 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in p)
                or not 0 <= p[0] < 384 or not 0 <= p[1] < 256):
            raise Problem(f'{label}: point must be finite and inside [0,384) x [0,256)')

    def box(b, label, optional=True):
        if b is None and optional:
            return
        if (not isinstance(b, list) or len(b) != 4 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in b)
                or not 0 <= b[0] < b[2] <= 384 or not 0 <= b[1] < b[3] <= 256):
            raise Problem(f'{label}: box must be valid xyxy within 384 x 256')

    instances = v.get('instances')
    regions = v.get('uncertain_regions')
    if instances is not None and (not isinstance(instances, list) or len(instances) > 200):
        raise Problem('instances must be null or an array (maximum 200)')
    if regions is not None and (not isinstance(regions, list) or len(regions) > 200):
        raise Problem('uncertain_regions must be null or an array (maximum 200)')
    ids = set()
    for b in instances or []:
        if not isinstance(b, dict) or not re.fullmatch(r'b[1-9]\d*', str(b.get('instance_id', ''))):
            raise Problem('Every bird needs a stable instance_id such as b1')
        bid = b['instance_id']
        if bid in ids:
            raise Problem('Duplicate bird instance_id')
        ids.add(bid)
        if not isinstance(b.get('notes',''),str) or len(b.get('notes',''))>10000:
            raise Problem(f'{bid}: notes must be text, at most 10000 characters')
        box(b.get('bird_bbox_xyxy'), f'{bid}.bird')
        box(b.get('head_bbox_xyxy'), f'{bid}.head')
        eyes = b.get('eyes', [])
        if not isinstance(eyes, list) or len(eyes) > 2:
            raise Problem(f'{bid}: at most two visible eyes')
        eids = set()
        for e in eyes:
            if not isinstance(e, dict) or not re.fullmatch(r'e[1-9]\d*', str(e.get('eye_id', ''))):
                raise Problem(f'{bid}: eye needs eye_id such as e1')
            if e['eye_id'] in eids:
                raise Problem(f'{bid}: duplicate eye_id')
            eids.add(e['eye_id'])
            point(e.get('center_xy'), f'{bid}.{e["eye_id"]}', False)
            box(e.get('bbox_xyxy'), f'{bid}.{e["eye_id"]}.box')
            if e.get('side', 'unknown') not in ('left', 'right', 'unknown'):
                raise Problem('Eye side must be anatomical left/right or unknown')
            eb = e.get('bbox_xyxy')
            if eb and not (eb[0] <= e['center_xy'][0] < eb[2] and eb[1] <= e['center_xy'][1] < eb[3]):
                raise Problem('Eye center must lie inside its optional eye box')
        visibility = b.get('part_visibility', {})
        if any(visibility.get(p, 'unknown') not in VISIBILITY for p in PARTS):
            raise Problem(f'{bid}: invalid visibility')
        if (eyes and visibility.get('eye') in ('hidden', 'out_of_frame')) or (b.get('head_bbox_xyxy') and visibility.get('head') in ('hidden', 'out_of_frame')):
            raise Problem(f'{bid}: visible geometry conflicts with hidden/out-of-frame visibility')
        for name, allowed in [
            ('invisibility_reasons', {'occlusion', 'pose', 'defocus', 'motion_blur', 'too_small', 'compression', 'out_of_frame', 'unknown'}),
            ('occluder_types', {'none', 'branch', 'leaf', 'dense_foliage', 'trunk', 'grass', 'other_bird', 'other', 'unknown'}),
            ('occluded_parts', set(PARTS))]:
            items = b.get(name, [])
            if not isinstance(items, list) or any(x not in allowed for x in items):
                raise Problem(f'{bid}: invalid {name}')
        target = b.get('af_reference_target_input', 'unknown')
        if target not in TARGETS or b.get('target_mode', 'auto') not in ('auto', 'manual'):
            raise Problem('Invalid input AF target')
        point(b.get('af_anchor_input_xy'), f'{bid}.anchor')
        if not b.get('bird_bbox_xyxy'):
            issues.append({'code': 'bird_box_required', 'instance_id': bid, 'severity': 'error'})
        if target == 'eye' and not eyes or target == 'head' and not b.get('head_bbox_xyxy') or target == 'body' and not b.get('bird_bbox_xyxy'):
            issues.append({'code': 'target_geometry_required', 'instance_id': bid, 'severity': 'error'})
        if target in ('eye', 'head', 'body') and b.get('af_anchor_input_xy') is None:
            issues.append({'code': 'anchor_required', 'instance_id': bid, 'severity': 'error'})
        anchor = b.get('af_anchor_input_xy')
        if anchor is not None and target in ('eye','head','body'):
            inside = lambda rect: rect is not None and rect[0] <= anchor[0] < rect[2] and rect[1] <= anchor[1] < rect[3]
            usable = (any(inside(e.get('bbox_xyxy')) or math.dist(anchor,e['center_xy']) <= 1.5 for e in eyes)
                      if target=='eye' else inside(b.get('head_bbox_xyxy') if target=='head' else b.get('bird_bbox_xyxy')))
            if not usable:
                issues.append({'code':'anchor_outside_target','instance_id':bid,'severity':'error'})
        if target in ('none', 'unknown') and b.get('af_anchor_input_xy') is not None:
            raise Problem('none/unknown target must not contain a focus anchor')
        bb = b.get('bird_bbox_xyxy')
        if bb:
            pts = [e['center_xy'] for e in eyes]
            hb = b.get('head_bbox_xyxy')
            if hb:
                pts += [[hb[0], hb[1]], [hb[2], hb[3]]]
            if any(not bb[0]-.5 <= p[0] <= bb[2]+.5 or not bb[1]-.5 <= p[1] <= bb[3]+.5 for p in pts):
                issues.append({'code': 'part_outside_bird', 'instance_id': bid, 'severity': 'warning'})
    rids = set()
    for r in regions or []:
        if not isinstance(r, dict) or not re.fullmatch(r'u[1-9]\d*', str(r.get('region_id', ''))):
            raise Problem('Uncertain region needs region_id such as u1')
        if r['region_id'] in rids:
            raise Problem('Duplicate uncertain region ID')
        rids.add(r['region_id'])
        box(r.get('bbox_xyxy'), 'uncertain region', False)
        if not isinstance(r.get('reason',''),str) or len(r.get('reason',''))>2000:
            raise Problem('Uncertain region reason must be text, at most 2000 characters')
    if v.get('presence') == 'absent' and (instances or regions):
        raise Problem('Confirmed absent image cannot contain birds or uncertain regions')
    if status == 'pending' and (instances is not None or regions is not None or v.get('presence') is not None):
        raise Problem('Use draft for an edited annotation; pending means uninspected')
    if status in ('annotated', 'reviewed'):
        if instances is None or regions is None or v.get('presence') is None:
            issues.append({'code': 'whole_image_check_required', 'severity': 'error'})
        if v.get('presence') == 'present' and not instances:
            issues.append({'code': 'present_requires_bird', 'severity': 'error'})
        if v.get('presence') == 'uncertain' and not regions:
            issues.append({'code': 'uncertain_requires_region', 'severity': 'error'})
        if any(i['severity'] == 'error' for i in issues):
            raise Problem('Complete required annotations before submission', details=issues)
    return v, issues


class Store:
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'annotations.sqlite3'
        with self.connect() as c:
            c.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS images(id TEXT PRIMARY KEY, metadata TEXT NOT NULL, predictions TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY REFERENCES images(id), revision INTEGER NOT NULL, document TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(id,revision));
                CREATE TABLE IF NOT EXISTS claims(id TEXT PRIMARY KEY REFERENCES images(id), actor TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS z8_reviews(id TEXT PRIMARY KEY REFERENCES images(id), revision INTEGER NOT NULL, document TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS z8_review_history(id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(id,revision));
            ''')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            with c:
                yield c
        finally:
            c.close()

    def metadata(self, image_id, conn=None):
        if not ID.fullmatch(image_id):
            raise Problem('Unknown image', 404)
        if conn is None:
            with self.connect() as c:
                return self.metadata(image_id, c)
        row = conn.execute('SELECT metadata FROM images WHERE id=?', (image_id,)).fetchone()
        if row is None:
            raise Problem('Unknown image', 404)
        return json.loads(row[0])

    def get(self, image_id, conn=None):
        if conn is None:
            with self.connect() as c:
                return self.get(image_id, c)
        meta = self.metadata(image_id, conn)
        row = conn.execute('SELECT * FROM annotations WHERE id=?', (image_id,)).fetchone()
        return {'image_id': image_id, 'revision': row['revision'] if row else 0,
                'annotation': json.loads(row['document']) if row else initial(meta),
                'updated': row['updated'] if row else None}

    def dataset(self):
        with self.connect() as c:
            labels = {r['id']: r for r in c.execute('SELECT * FROM annotations')}
            claims = {r['id']: r for r in c.execute('SELECT * FROM claims WHERE expires>?', (time.time(),))}
            result = []
            for row in c.execute('SELECT * FROM images ORDER BY id'):
                meta, pred = json.loads(row['metadata']), json.loads(row['predictions'])
                saved = labels.get(row['id'])
                a = json.loads(saved['document']) if saved else initial(meta)
                result.append({'image_id': row['id'], 'batch': meta['batch'],
                    'width': 384, 'height': 256, 'candidate_count': len(pred),
                    'status': a['annotation_status'], 'presence': a['presence'],
                    'decision': a['review_decision'], 'revision': saved['revision'] if saved else 0,
                    'bird_count': len(a['instances'] or []), 'reference_available': bool(meta.get('reference_path')),
                    'claimed_by': json.loads(claims[row['id']]['actor']) if row['id'] in claims else None})
            return result

    def image(self, image_id):
        meta = self.metadata(image_id)
        with self.connect() as c:
            pred = json.loads(c.execute('SELECT predictions FROM images WHERE id=?', (image_id,)).fetchone()[0])
        return {'image_id': image_id, 'width': 384, 'height': 256,
                'batch': meta['batch'], 'png_sha256': meta['png_sha256'], 'input_sha256': meta['input_sha256'],
                'preprocess_id': meta['preprocess_id'], 'predictions': pred,
                'reference': {'available': bool(meta.get('reference_path')), 'width': meta.get('reference_width'),
                              'height': meta.get('reference_height'), 'sha256': meta.get('reference_sha256')}}

    def save_many(self, records, who):
        who = actor(who)
        if not isinstance(records, list) or not 1 <= len(records) <= 1000:
            raise Problem('records must contain 1-1000 items')
        if any(not isinstance(record,dict) for record in records):
            raise Problem('Every imported record must be an object')
        if len({r.get('image_id') for r in records}) != len(records):
            raise Problem('Duplicate image in transaction')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            prepared = []
            for record in records:
                ident = record.get('image_id', '')
                current = self.get(ident, c)
                if type(record.get('base_revision')) is not int or record['base_revision'] != current['revision']:
                    raise Problem('Revision conflict: reload before editing', 409,
                                  {'image_id': ident, 'current_revision': current['revision']})
                v, issues = validate(record.get('annotation'), self.metadata(ident, c))
                old = current['annotation']
                if v['annotation_status'] == 'reviewed':
                    if who['kind'] != 'human':
                        raise Problem('AI annotations require human review before reviewed status')
                    if old['annotation_status'] not in ('annotated', 'reviewed'):
                        raise Problem('Submit the annotation before human review')
                    comparable = lambda a: {k: x for k, x in a.items() if k not in ('annotation_status', 'provenance', 'review')}
                    if comparable(v) != comparable(old):
                        raise Problem('Save annotation edits before marking reviewed')
                    previous = old.get('provenance') or {}
                    v['review'] = {'reviewer': who, 'at': now(),
                        'independent': (previous.get('content_actor') or {}).get('id') != who['id']}
                else:
                    v['review'] = None
                revision, stamp = current['revision'] + 1, now()
                old_provenance = old.get('provenance') or {}
                content_actor = old_provenance.get('content_actor', who) if v['annotation_status'] == 'reviewed' else who
                v['provenance'] = {'actor': who, 'content_actor': content_actor, 'at': stamp,
                                   'revision': revision, 'parent_revision': current['revision'], 'protocol': SCHEMA}
                prepared.append((ident, revision, stamp, v, issues))
            for ident, revision, stamp, v, issues in prepared:
                c.execute('INSERT INTO annotations VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,document=excluded.document,updated=excluded.updated',
                          (ident, revision, dumps(v), stamp))
                c.execute('INSERT INTO history VALUES(?,?,?,?,?)', (ident, revision, dumps(v), dumps(who), stamp))
                c.execute('DELETE FROM claims WHERE id=? AND actor=?', (ident, dumps(who)))
            return [{'image_id': ident, 'revision': rev, 'annotation': v, 'updated': stamp, 'issues': issues}
                    for ident, rev, stamp, v, issues in prepared]

    def history(self, ident):
        self.metadata(ident)
        with self.connect() as c:
            return [{'revision': r['revision'], 'actor': json.loads(r['actor']), 'created': r['created'],
                     'annotation': json.loads(r['document'])}
                    for r in c.execute('SELECT * FROM history WHERE id=? ORDER BY revision DESC', (ident,))]

    def claim(self, who, seconds=600, zero_only=False):
        who = actor(who)
        if type(seconds) is not int or not 30 <= seconds <= 3600:
            raise Problem('Claim seconds must be between 30 and 3600')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for row in c.execute('SELECT * FROM images ORDER BY id'):
                ident = row['id']
                a = self.get(ident, c)
                if a['annotation']['annotation_status'] not in ('pending', 'draft'):
                    continue
                if zero_only and json.loads(row['predictions']):
                    continue
                claim = c.execute('SELECT * FROM claims WHERE id=? AND expires>?', (ident, time.time())).fetchone()
                if claim is not None:
                    continue
                expiry = time.time() + seconds
                c.execute('INSERT INTO claims VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET actor=excluded.actor,expires=excluded.expires',
                          (ident, dumps(who), expiry))
                return {**a, 'expires_at': expiry, 'image': self.image_in_connection(ident, c)}
            return None

    def image_in_connection(self, ident, c):
        meta = self.metadata(ident, c)
        return {'image_id': ident, 'png_sha256': meta['png_sha256'], 'input_sha256': meta['input_sha256'],
                'width': 384, 'height': 256, 'image_url': f'/api/images/{ident}/png'}

    def release_claim(self, ident, who):
        who = actor(who)
        with self.connect() as c:
            c.execute('DELETE FROM claims WHERE id=? AND actor=?', (ident, dumps(who)))

    def export(self, scope='all'):
        if scope not in ('all', 'complete', 'reviewed'):
            raise Problem('Invalid export scope')
        with self.connect() as c:
            rows = []
            for row in c.execute('SELECT id FROM images ORDER BY id'):
                record = self.get(row['id'], c)
                status = record['annotation']['annotation_status']
                if scope == 'complete' and status not in ('annotated', 'reviewed') or scope == 'reviewed' and status != 'reviewed':
                    continue
                rows.append(record)
            return rows

    def backup(self):
        folder = self.root / 'backups'
        folder.mkdir(exist_ok=True)
        target = folder / (dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
        with self.connect() as source, closing(sqlite3.connect(target)) as dest:
            source.backup(dest)
        return target
