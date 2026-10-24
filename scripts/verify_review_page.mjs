import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const root = process.argv[2];
assert.ok(root, 'Pass the local run directory');
const predictions = fs.readFileSync(path.join(root, 'predictions.jsonl'), 'utf8').trim().split(/\r?\n/).map(JSON.parse);
const expectedImages = predictions.length;
const expectedZero = predictions.filter(r => r.candidates.length === 0).length;
const html = fs.readFileSync(path.join(root, 'review-bilingual.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const storageKey = script.match(/const key='([^']+)'/)[1];
const store = new Map();
const nodes = new Map();
let selects = [], notes = [], clicks = [];
function node(id) {
  if (!nodes.has(id)) {
    const item = {value: id === 'filter' ? 'all' : '', textContent: '', _html: ''};
    Object.defineProperty(item, 'innerHTML', {
      get() { return this._html; },
      set(value) {
        this._html = value;
        if (id === 'grid') {
          selects = [...value.matchAll(/data-id="([^"]+)"/g)].map(m => ({dataset: {id: m[1]}, value: ''}));
          notes = [...value.matchAll(/data-note="([^"]+)"/g)].map(m => ({dataset: {note: m[1]}, value: ''}));
        }
      }
    });
    nodes.set(id, item);
  }
  return nodes.get(id);
}
const context = vm.createContext({
  document: {
    documentElement: {lang: "en"},
    getElementById: node,
    querySelectorAll: selector => selector === '[data-id]' ? selects : notes,
    createElement: () => ({click() { clicks.push({download: this.download, href: this.href}); }})
  },
  localStorage: {getItem: k => store.get(k), setItem: (k, v) => store.set(k, v)},
  Blob, URL, Date, JSON, setTimeout: fn => { fn(); return 0; }
});
new vm.Script(script).runInContext(context);
const count = () => (node('grid').innerHTML.match(/<article/g) || []).length;
assert.equal(count(), expectedImages);
assert.equal(node("title").textContent, "Z8 candidate review");
node("language").value="zh-CN"; node("language").onchange();
assert.equal(node("title").textContent, "Z8 候选框复核");
node("language").value="en"; node("language").onchange();
node('filter').value = 'zero'; node('filter').onchange(); assert.equal(count(), expectedZero);
node('filter').value = 'all'; node('filter').onchange();
selects[0].value = 'error'; selects[0].onchange();
assert.equal(JSON.parse(store.get(storageKey))[predictions[0].image_id].decision, 'error');
node('filter').value = 'error'; node('filter').onchange(); assert.equal(count(), 1);
node('toggle').onclick(); assert.ok(node('grid').innerHTML.includes('public-images'));
node('export').onclick(); assert.equal(clicks[0].download, 'z8-review-decisions.json');
const rows = html.match(/const rows=([\s\S]*?);let overlay/)[1];
for (const row of JSON.parse(rows)) {
  for (const name of [row.overlay, row.image]) assert.ok(fs.existsSync(path.resolve(root, name)), name);
}
const report = {passed: true, images: expectedImages, zeroCandidateFilter: expectedZero, storageKey,
  checks: ['JavaScript parse', 'English default', 'Simplified Chinese switch', 'all cards', 'zero-candidate filter', 'decision serialization',
    'error filter', 'original/overlay switch', 'export trigger', 'all image links exist'],
  scope: 'Pure JavaScript logic with an in-memory DOM stub; no browser automation or layout verification.'};
fs.writeFileSync(path.join(root, 'review-bilingual-qa.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
