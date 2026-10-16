import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const bundle = readFileSync(new URL('../site/vendor/model-viewer.min.js', import.meta.url), 'utf8');
const upstreamGuard = 'if(void 0!==e.userData.pivot&&i.length>0)';
const patchedGuard = 'if(Array.isArray(e.userData.pivot)&&e.userData.pivot.length===3&&e.userData.pivot.every(Number.isFinite)&&i.length>0)';
const start = bundle.indexOf(patchedGuard);
const end = bundle.indexOf('return e})}_loadNodeShallow(t){', start);
assert.ok(start >= 0 && end > start, 'Expected bundled GLTFLoader pivot conversion');
// Execute the shipped branch, so a reverted or malformed vendor patch fails here.
const applyPivot = new Function('e', 'i', 'vn', bundle.slice(start, end) + 'return e;');

class Vector3 {
  constructor(x = 0, y = 0, z = 0) { this.set(x, y, z); }
  set(x, y, z) { Object.assign(this, { x, y, z }); return this; }
  fromArray(values) { return this.set(...values); }
}

function fixture(pivot, withChild = true) {
  const parent = { userData: { pivot }, position: new Vector3(10, 20, 30), pivot: null };
  const children = withChild ? [{ position: new Vector3(4, 5, 6) }] : [];
  return { parent, children };
}

test('human-readable pivot metadata does not change transforms', () => {
  const description = 'bottom center of nominal closed envelope';
  const { parent, children } = fixture(description);
  applyPivot(parent, children, Vector3);
  assert.equal(parent.userData.pivot, description);
  assert.equal(parent.pivot, null);
  assert.deepEqual(parent.position, new Vector3(10, 20, 30));
  assert.deepEqual(children[0].position, new Vector3(4, 5, 6));
});

test('finite numeric vector preserves the upstream pivot conversion', () => {
  const { parent, children } = fixture([1, 2, 3]);
  applyPivot(parent, children, Vector3);
  assert.deepEqual(parent.pivot, new Vector3(1, 2, 3));
  assert.deepEqual(parent.position, new Vector3(9, 18, 27));
  assert.deepEqual(children[0].position, new Vector3());
  assert.equal(Object.hasOwn(parent.userData, 'pivot'), false);
});

test('malformed values remain metadata and never corrupt transforms', () => {
  for (const value of [null, undefined, 2, {}, [], [1, 2], [1, 2, 3, 4], ['1', 2, 3], [NaN, 2, 3], [1, Infinity, 3]]) {
    const { parent, children } = fixture(value);
    applyPivot(parent, children, Vector3);
    assert.equal(parent.userData.pivot, value);
    assert.equal(parent.pivot, null);
    assert.deepEqual(parent.position, new Vector3(10, 20, 30));
    assert.deepEqual(children[0].position, new Vector3(4, 5, 6));
  }
});

test('nodes without children retain their metadata and transform', () => {
  const value = [1, 2, 3];
  const { parent, children } = fixture(value, false);
  applyPivot(parent, children, Vector3);
  assert.equal(parent.userData.pivot, value);
  assert.equal(parent.pivot, null);
  assert.deepEqual(parent.position, new Vector3(10, 20, 30));
});

test('the guard is the only change from the pinned upstream distribution', () => {
  assert.equal(bundle.split(patchedGuard).length, 2);
  assert.equal(bundle.includes(upstreamGuard), false);
  const upstream = bundle.replace(patchedGuard, upstreamGuard);
  assert.equal(createHash('sha256').update(upstream).digest('hex'), '283b0672384614b4847636c306fc93fe4b1fcadc76d668b4e47f0ca76bcf033b');
  assert.equal(createHash('sha256').update(bundle).digest('hex'), '22bd28e639df581c1cf59ccebd51cee7b437ddf095eac1d8392d24baec2f38b8');
});
