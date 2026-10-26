/* Human point-availability decisions are separate from AI diagnostic drafts. */
(function (root) {
  'use strict';
  const copy = value => JSON.parse(JSON.stringify(value));
  const canonical = value => JSON.stringify(value, (key, item) => item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(k => [k, item[k]])) : item);
  const choices = ['supported', 'unsupported', 'unknown'];
  const eyes = ['yes', 'no', 'unknown'];
  const parts = ['eye', 'head', 'body', 'unknown'];

  class PointReview {
    constructor(items, datasetId) {
      this.items = items;
      this.datasetId = datasetId;
      this.records = Object.fromEntries(items.map(item => [item.image_id, {
        image_id: item.image_id, candidate_id: item.candidate_id, revision: 0,
        input_sha256: item.input_sha256, point_xy: copy(item.point_xy),
        choice: null, eye_localizable_input: 'unknown', part: 'unknown', note: '',
        actor_kind: 'human', status: 'draft', human_confirmed: false,
        accepted_for_training: false, history: []
      }]));
      if (Object.keys(this.records).length !== items.length) throw Error('图片编号重复');
    }
    get(id) {
      if (!Object.hasOwn(this.records, id)) throw Error('未知图片编号');
      return copy(this.records[id]);
    }
    edit(id, fields) {
      const old = this.get(id);
      const next = {...old, ...fields};
      if (Object.keys(fields).some(k => !['eye_localizable_input', 'part', 'note'].includes(k))) throw Error('不支持的编辑字段');
      this.validateFields(next);
      if (JSON.stringify(fields) === JSON.stringify(Object.fromEntries(Object.keys(fields).map(k => [k, old[k]])))) return;
      const prior = copy(old); delete prior.history;
      this.records[id] = {...next, revision: old.revision + 1, status: 'draft', human_confirmed: false,
        history: [...old.history, prior], accepted_for_training: false};
    }
    validateFields(value) {
      if (!eyes.includes(value.eye_localizable_input) || !parts.includes(value.part) ||
          typeof value.note !== 'string' || value.note.length > 2000) throw Error('复核字段不合法');
    }
    confirm(id, choice) {
      if (!choices.includes(choice)) throw Error('请选择可用、不可用或看不清');
      const old = this.get(id), prior = copy(old); delete prior.history;
      this.records[id] = {...old, choice, revision: old.revision + 1,
        actor_kind: 'human', status: 'confirmed', human_confirmed: true, accepted_for_training: false,
        confirmed_at_utc: new Date().toISOString(), history: [...old.history, prior]};
    }
    unconfirm(id) {
      const old = this.get(id), prior = copy(old); delete prior.history;
      this.records[id] = {...old, revision: old.revision + 1, status: 'draft', human_confirmed: false,
        accepted_for_training: false, history: [...old.history, prior]};
    }
    stats() {
      const result = {total: this.items.length, confirmed: 0, supported: 0, unsupported: 0, unknown: 0};
      for (const value of Object.values(this.records)) if (value.human_confirmed && value.status === 'confirmed') {
        result.confirmed++; result[value.choice]++;
      }
      return result;
    }
    export() {
      return {schema: 'point-surface-human-review-v1', dataset_id: this.datasetId,
        exported_at_utc: new Date().toISOString(), records: copy(Object.values(this.records)),
        old_development_data: true, accepted_for_training: false};
    }
    restore(payload) {
      if (payload.schema !== 'point-surface-human-review-v1' || payload.dataset_id !== this.datasetId ||
          !Array.isArray(payload.records)) throw Error('文件不属于这批落点');
      const ids = new Set(), changes = [];
      for (const value of payload.records) {
        const old = this.get(value.image_id);
        if (ids.has(value.image_id) || value.candidate_id !== old.candidate_id ||
            value.input_sha256 !== old.input_sha256 || canonical(value.point_xy) !== canonical(old.point_xy)) throw Error('落点身份不匹配');
        ids.add(value.image_id);
        if (!Number.isInteger(value.revision) || value.revision < 0 || value.revision > 100000 ||
            value.actor_kind !== 'human' || value.accepted_for_training !== false ||
            !Array.isArray(value.history)) throw Error('复核来源或修订不合法');
        this.validateFields(value);
        if (value.status === 'confirmed') {
          if (value.human_confirmed !== true || !choices.includes(value.choice) ||
              !Number.isFinite(Date.parse(value.confirmed_at_utc))) throw Error('人工确认记录不完整');
        } else if (value.status !== 'draft' || value.human_confirmed !== false) throw Error('草稿不能冒充人工确认');
        if (value.revision > old.revision) changes.push(copy(value));
        else if (value.revision === old.revision && canonical(value) !== canonical(old)) throw Error('相同修订存在冲突');
      }
      for (const value of changes) this.records[value.image_id] = value;
      return changes.length;
    }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = PointReview;
  else root.PointReview = PointReview;
})(globalThis);
