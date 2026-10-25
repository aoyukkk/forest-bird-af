"use strict";
const $ = (id) => document.getElementById(id),
  clone = (v) => structuredClone(v),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const SVG = "http://www.w3.org/2000/svg";
const words = {
  zh: {
    brand: "林鸟标注台",
    actor: "标注者",
    help: "使用帮助",
    export: "导出 / 备份",
    queue: "素材队列",
    more: "显示更多",
    localOnly: "本地保存 · 人与 AI 共用",
    inputDataset: "Z8 模拟输入数据集",
    select: "选择",
    bird: "鸟框",
    head: "头框",
    eye: "眼点",
    anchor: "对焦点",
    uncertain: "疑似",
    z8Overlay: "Z8 候选框",
    manualOverlay: "当前标注",
    pixels: "像素显示",
    fit: "适应",
    reference: "查看原图参考 ↗",
    history: "修订历史",
    ruleTitle: "标全可见部位，再决定锁哪里",
    ruleText:
      "鸟 → 头 → 可见眼全部标注；眼被遮挡时不猜位置。当前坐标与可见性以 384×256 输入为准。",
    noBird: "已检查：无鸟",
    discuss: "需要裁决",
    save: "保存草稿",
    review: "通过复核",
    complete: "完成初标并下一张 →",
    properties: "标注详情",
    all: "全部状态",
    pending: "未开始",
    draft: "草稿",
    annotated: "已初标",
    reviewed: "已复核",
    needs_adjudication: "需裁决",
    allPred: "全部素材",
    zeroPred: "Z8 无候选",
    hasPred: "Z8 有候选",
    allBatches: "所有批次",
    search: "搜索编号，如 0122",
    saved: "已保存",
    saving: "正在保存…",
    unsaved: "待保存",
    offline: "连接失败",
    conflict: "修订冲突",
    progress: "初标完成",
    of: "/",
    image: "图片",
    birds: "鸟实例",
    newBird: "+ 新鸟",
    noLabels: "先用 B 画鸟框，再用 H 画头框、E 点眼。多只鸟分别建实例。",
    target: "输入尺度优先目标",
    auto: "自动：眼 → 头 → 身",
    eyeTarget: "眼",
    headTarget: "头",
    bodyTarget: "鸟身",
    noneTarget: "无可用部位",
    unknownTarget: "不确定",
    anchorNeeded: "请用 P 在可见部位上指定对焦点",
    visibility: "部位可见性",
    visible: "可见",
    partial: "部分可见",
    hidden: "被挡 / 不可见",
    out_of_frame: "出画",
    unknown: "不确定",
    occluders: "遮挡物",
    reasons: "不可定位的原因",
    branch: "树枝",
    leaf: "树叶",
    dense_foliage: "密集枝叶",
    trunk: "树干",
    grass: "草",
    other_bird: "其他鸟",
    other: "其他",
    none: "无",
    occlusion: "遮挡",
    pose: "姿态 / 背向",
    defocus: "失焦",
    motion_blur: "运动模糊",
    too_small: "太小",
    compression: "压缩",
    notes: "整图备注",
    birdNotes: "当前鸟备注",
    decision: "Z8 候选位置复核",
    unassessed: "尚未判断",
    reasonable: "候选位置合理",
    error: "漏检 / 误框",
    uncertainDecision: "不确定",
    decisionHelp: "只判断候选位置；这不是机身最终对焦准确率。",
    referenceViewed: "已查看原图参考；当前标签仍只描述输入图",
    geometry: "选中形状坐标",
    delete: "删除",
    deleteBird: "删除当前鸟",
    eyeBox: "补眼框",
    eyeBoxHint: "为当前眼拖出可辨边界；不要造固定大小眼框。",
    side: "眼的解剖学方向",
    left: "鸟自身左眼",
    right: "鸟自身右眼",
    unknownSide: "方向未知",
    uncertainRegions: "疑似区域",
    rawPred: "Z8 原始候选",
    predHelp:
      "仅供参考。slot 0/4 鸟身，1 头，2/3 眼，5 辅助区域。采用后需人工修正，不能批量当真值。",
    adoptBird: "作为鸟框",
    adoptHead: "作为头框",
    adoptEye: "作为眼点",
    noPred: "这张图没有 Z8 候选，请检查是否漏鸟。",
    selectBird: "先选择所属鸟，或用 B 建一个鸟框。",
    twoEyes: "每只鸟最多标两只可见眼。",
    smallBox: "框太小，请拖动至少一个输入像素。",
    noSelection: "先选中一个形状。",
    deleted: "已删除；Ctrl+Z 可撤销。",
    savedToast: "草稿已保存",
    completeToast: "初标已保存",
    reviewToast: "复核已保存",
    noneConfirmed: "已记录无鸟，请完成初标保存检查结果。",
    noBirdWithShapes: "已有鸟或疑似区域，请先核对并删除相应标注。",
    needPresence: "请画出可辨鸟、标疑似区域，或明确选择“已检查：无鸟”。",
    nextEnd: "已到队列末尾",
    loadError: "载入失败",
    unsavedExit: "有尚未保存的标注。",
    inputSpace: "坐标：384 × 256 输入",
    reasonRequired: "请补充相关信息",
    referenceHelp:
      "原图只作参考，不在此画框。返回输入图后，只标输入中可辨的部位。",
    aiTitle: "人和 AI 操作同一份标注",
    helpTitle: "从一只鸟开始",
    exportTitle: "导出、导入与备份",
    allExport: "导出全部工程记录 JSONL",
    completeExport: "导出已初标 / 已复核 JSONL",
    reviewedExport: "仅导出已复核 JSONL",
    import: "导入修改后的 JSONL",
    backup: "创建数据库快照",
    exportHelp:
      "JSONL 保留眼点、实例关系、可见性和修订号。草稿不自动进入“已初标”导出。导入会检查图像哈希与修订号，冲突时整批不写入。",
    backupDone: "数据库快照已创建",
    importDone: "导入完成",
    importEmpty: "文件没有标注记录",
    historyTitle: "修订历史",
    restore: "恢复为新草稿",
    noHistory: "还没有保存的修订。",
    restoreDone: "历史内容已恢复为新草稿，旧修订保留。",
    selfReview: "非独立自复核",
    independentReview: "独立复核",
    aiReview: "AI 初标需要人工复核",
    recovery: "发现本机未保存的草稿",
    recover: "恢复草稿",
    downloadDraft: "下载本机草稿",
    latest: "备份草稿并载入最新",
    remoteChange: "另一位标注者已更新这张图",
    reload: "载入最新",
    conflictHelp:
      "其他窗口或 AI 已保存新修订。本机草稿已保留，先备份再载入最新版本，避免覆盖。",
    invalidCoords: "坐标无效；框应在 384×256 内且宽高大于零。",
    validation: "请补全标注",
    bird_box_required: "缺少整鸟框",
    target_geometry_required: "优先目标没有对应部位",
    anchor_required: "缺少可见参考对焦点",
    anchor_outside_target: "参考对焦点不在所选部位内",
    whole_image_check_required: "尚未完成全图检查",
    present_requires_bird: "有鸟但未标鸟框",
    uncertain_requires_region: "请框出疑似区域",
    part_outside_bird: "头或眼超出整鸟框，请核对",
    loading: "正在载入素材…",
    noMatches: "没有符合筛选条件的素材",
    zoomHint: "滚轮缩放 · 空格拖动 · F 适应",
    selectHint: "拖动移动；拖四角调整大小。B 鸟 / H 头 / E 眼 / P 对焦点",
    birdHint: "拖出全部可见鸟的外接框。每次画鸟框新建一只鸟。",
    headHint: "先选所属鸟，再拖出可见头部范围（含喙）。",
    eyeHint: "先选所属鸟，再单击可见眼的中心。",
    anchorHint: "单击实际可见部位；不要让对焦点落到树枝。",
    uncertainHint: "拖出疑似区域，不把不确定目标当作无鸟。",
    eyeBoxMode: "眼框",
    noEyeBox: "删除眼框",
    allDone: "当前筛选队列没有下一张待标图片",
    owner: "来源",
    human: "人工",
    ai: "AI",
    refresh: "刷新队列",
  },
  en: {
    brand: "Forest Bird Annotator",
    actor: "Annotator",
    help: "Help",
    export: "Export / backup",
    queue: "Image queue",
    more: "Load more",
    localOnly: "Local storage · Human + AI",
    inputDataset: "Z8 SIMULATION INPUT DATASET",
    select: "Select",
    bird: "Bird",
    head: "Head",
    eye: "Eye",
    anchor: "Anchor",
    uncertain: "Uncertain",
    z8Overlay: "Z8 proposals",
    manualOverlay: "Annotations",
    pixels: "Pixel view",
    fit: "Fit",
    reference: "Original reference ↗",
    history: "History",
    ruleTitle: "Label visible parts, then choose the target",
    ruleText:
      "Label bird, head and every visible eye. Never infer a hidden eye. Coordinates and visibility describe the 384×256 input.",
    noBird: "Checked: no bird",
    discuss: "Needs adjudication",
    save: "Save draft",
    review: "Mark reviewed",
    complete: "Submit & next →",
    properties: "Annotation details",
    all: "All statuses",
    pending: "Not started",
    draft: "Draft",
    annotated: "Annotated",
    reviewed: "Reviewed",
    needs_adjudication: "Needs adjudication",
    allPred: "All images",
    zeroPred: "No Z8 proposals",
    hasPred: "Has Z8 proposals",
    allBatches: "All batches",
    search: "Search ID, e.g. 0122",
    saved: "Saved",
    saving: "Saving…",
    unsaved: "Unsaved",
    offline: "Connection failed",
    conflict: "Revision conflict",
    progress: "Submitted",
    of: "/",
    image: "Image",
    birds: "Bird instances",
    newBird: "+ Bird",
    noLabels:
      "Draw a bird with B, head with H and eye centers with E. Create a separate instance for each bird.",
    target: "Preferred target at input scale",
    auto: "Automatic: eye → head → bird",
    eyeTarget: "Eye",
    headTarget: "Head",
    bodyTarget: "Bird",
    noneTarget: "No usable part",
    unknownTarget: "Unknown",
    anchorNeeded: "Use P to mark a visible focus anchor",
    visibility: "Part visibility",
    visible: "Visible",
    partial: "Partial",
    hidden: "Hidden / not visible",
    out_of_frame: "Out of frame",
    unknown: "Unknown",
    occluders: "Occluders",
    reasons: "Why unavailable",
    branch: "Branch",
    leaf: "Leaf",
    dense_foliage: "Dense foliage",
    trunk: "Trunk",
    grass: "Grass",
    other_bird: "Other bird",
    other: "Other",
    none: "None",
    occlusion: "Occlusion",
    pose: "Pose / facing away",
    defocus: "Defocus",
    motion_blur: "Motion blur",
    too_small: "Too small",
    compression: "Compression",
    notes: "Image notes",
    birdNotes: "Bird notes",
    decision: "Review Z8 proposal locations",
    unassessed: "Not assessed",
    reasonable: "Reasonable locations",
    error: "Miss / wrong box",
    uncertainDecision: "Uncertain",
    decisionHelp: "Reviews proposals, not final camera focus accuracy.",
    referenceViewed: "Original consulted; labels still describe input pixels",
    geometry: "Selected geometry",
    delete: "Delete",
    deleteBird: "Delete this bird",
    eyeBox: "Add eye box",
    eyeBoxHint:
      "Draw the visible eye boundary; do not invent a fixed-size box.",
    side: "Anatomical eye side",
    left: "Bird’s left eye",
    right: "Bird’s right eye",
    unknownSide: "Unknown side",
    uncertainRegions: "Uncertain regions",
    rawPred: "Raw Z8 proposals",
    predHelp:
      "Reference only. Slots 0/4: bird; 1: head; 2/3: eyes; 5: auxiliary region. Adopt individually and correct; never bulk-convert to truth.",
    adoptBird: "Use as bird",
    adoptHead: "Use as head",
    adoptEye: "Use as eye point",
    noPred: "No Z8 proposals. Check for missed birds.",
    selectBird: "Select a bird instance, or draw one with B.",
    twoEyes: "At most two visible eyes per bird.",
    smallBox: "Drag a box at least one input pixel wide and high.",
    noSelection: "Select a shape first.",
    deleted: "Deleted. Ctrl+Z to undo.",
    savedToast: "Draft saved",
    completeToast: "Annotation submitted",
    reviewToast: "Review saved",
    noneConfirmed: "No bird recorded. Submit to finish the image check.",
    noBirdWithShapes:
      "Birds or uncertain regions already exist; inspect and remove them first.",
    needPresence:
      "Label a visible bird, draw an uncertain region, or explicitly choose Checked: no bird.",
    nextEnd: "End of queue",
    loadError: "Could not load",
    unsavedExit: "There are unsaved annotations.",
    inputSpace: "Coordinates: 384 × 256 input",
    reasonRequired: "Complete relevant details",
    referenceHelp:
      "Read-only reference. Return to input pixels to annotate only parts visible at input scale.",
    aiTitle: "Humans and AI share the same annotation API",
    helpTitle: "Start with one bird",
    exportTitle: "Export, import and backup",
    allExport: "Export all project records (JSONL)",
    completeExport: "Export annotated / reviewed (JSONL)",
    reviewedExport: "Export reviewed only (JSONL)",
    import: "Import edited JSONL",
    backup: "Create database snapshot",
    exportHelp:
      "JSONL preserves points, instances, visibility and revisions. Drafts are excluded from submitted exports. Import validates hashes and revisions atomically.",
    backupDone: "Database snapshot created",
    importDone: "Import completed",
    importEmpty: "No annotation records in file",
    historyTitle: "Revision history",
    restore: "Restore as new draft",
    noHistory: "No saved revisions yet.",
    restoreDone:
      "Historical content restored as a new draft. Old revisions remain.",
    selfReview: "Non-independent self-review",
    independentReview: "Independent review",
    aiReview: "AI drafts require human review",
    recovery: "An unsaved local draft was found",
    recover: "Recover draft",
    downloadDraft: "Download local draft",
    latest: "Back up draft & load latest",
    remoteChange: "Another annotator updated this image",
    reload: "Load latest",
    conflictHelp:
      "Another window or AI saved a newer revision. Your local draft is retained. Back it up and load the latest version before editing.",
    invalidCoords:
      "Invalid coordinates. Boxes must have positive width/height within 384×256.",
    validation: "Complete annotation",
    bird_box_required: "Bird box required",
    target_geometry_required: "Target geometry required",
    anchor_required: "Visible focus anchor required",
    anchor_outside_target: "Focus anchor lies outside the selected part",
    whole_image_check_required: "Whole image check required",
    present_requires_bird: "Present image needs a bird instance",
    uncertain_requires_region: "Draw the uncertain region",
    part_outside_bird: "Head or eye lies outside bird box; inspect",
    loading: "Loading images…",
    noMatches: "No images match these filters",
    zoomHint: "Wheel: zoom · Space+drag: pan · F: fit",
    selectHint:
      "Drag to move; drag corners to resize. B bird / H head / E eye / P anchor",
    birdHint:
      "Draw the bounding box of all visible bird parts. Each box creates a new bird.",
    headHint:
      "Select the parent bird, then draw the visible head including the beak.",
    eyeHint: "Select the parent bird, then click the visible eye center.",
    anchorHint: "Click a visible part; avoid a branch inside the box.",
    uncertainHint:
      "Draw the uncertain region. Do not treat it as a clean negative.",
    eyeBoxMode: "Eye box",
    noEyeBox: "Remove eye box",
    allDone: "No next pending image in this filtered queue",
    owner: "Source",
    human: "Human",
    ai: "AI",
    refresh: "Refresh queue",
  },
};
const state = {
  lang: localStorage.getItem("fba-language") || "zh",
  rows: [],
  filtered: [],
  limit: 60,
  id: null,
  record: null,
  meta: null,
  a: null,
  rev: 0,
  tool: "select",
  selected: null,
  birdId: null,
  predSelected: null,
  dirty: false,
  serial: 0,
  saving: null,
  timer: null,
  blocked: false,
  undo: [],
  redo: [],
  gesture: null,
  space: false,
  view: { x: 0, y: 0, w: 384, h: 256 },
  loadToken: 0,
  transition: false,
};
const t = (k) => words[state.lang][k] || words.en[k] || k;
const palette = {
  bird: "#f08075",
  head: "#6ed5ae",
  eye: "#77baff",
  anchor: "#f1d181",
  uncertain: "#c294f3",
};
const slotColors = [
  "#ff5555",
  "#44ff99",
  "#44bbff",
  "#ffcc55",
  "#dd88ff",
  "#ffffff",
];
let toastTimer;
function toast(message, error = false) {
  $("toast").textContent = message;
  $("toast").className = "toast" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(
    () => $("toast").classList.add("hidden"),
    error ? 8000 : 3500,
  );
}
async function api(path, method = "GET", payload) {
  const response = await fetch(path, {
    method,
    headers: payload ? { "Content-Type": "application/json" } : {},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    const e = new Error(data.error || response.statusText);
    e.status = response.status;
    e.details = data.details;
    throw e;
  }
  return data;
}
function who() {
  return {
    id: $("actor").value.trim() || "reviewer-local",
    kind: localStorage.getItem("fba-actor-kind") === "ai" ? "ai" : "human",
  };
}
function connection(key) {
  $("connection").textContent = t(key);
  $("connection").className =
    "save-pill" +
    (["saving", "unsaved"].includes(key)
      ? " busy"
      : ["offline", "conflict"].includes(key)
        ? " error"
        : "");
}
function options(values, current) {
  return values
    .map(
      ([v, label]) =>
        `<option value="${esc(v)}" ${v === current ? "selected" : ""}>${esc(label)}</option>`,
    )
    .join("");
}
function setOptions(id, values) {
  const v = $(id).value;
  $(id).innerHTML = options(values, v || values[0][0]);
}
function translate() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  $("language").value = state.lang;
  document
    .querySelectorAll("[data-i18n]")
    .forEach((el) => (el.textContent = t(el.dataset.i18n)));
  $("search").placeholder = t("search");
  setOptions("statusFilter", [
    ["all", t("all")],
    ...["pending", "draft", "annotated", "reviewed", "needs_adjudication"].map(
      (k) => [k, t(k)],
    ),
  ]);
  setOptions("predictionFilter", [
    ["all", t("allPred")],
    ["zero", t("zeroPred")],
    ["has", t("hasPred")],
  ]);
  const batches = [...new Set(state.rows.map((r) => r.batch))];
  setOptions("batchFilter", [
    ["all", t("allBatches")],
    ...batches.map((b) => [b, b.replace("community-images-2026-10-24-", "")]),
  ]);
  filterQueue();
  renderProperties();
  setTool(state.tool);
  connection(
    state.blocked
      ? "conflict"
      : state.saving
        ? "saving"
        : state.dirty
          ? "unsaved"
          : "saved",
  );
}
function statusCounts() {
  const complete = state.rows.filter((r) =>
    ["annotated", "reviewed"].includes(r.status),
  ).length;
  const reviewed = state.rows.filter((r) => r.status === "reviewed").length;
  $("progressText").textContent =
    `${t("progress")} ${complete} / ${state.rows.length} · ${t("reviewed")} ${reviewed}`;
  $("progressFill").style.width =
    (100 * complete) / Math.max(1, state.rows.length) + "%";
}
function filterQueue() {
  const q = $("search").value.trim().toLowerCase();
  state.filtered = state.rows.filter(
    (r) =>
      (!q || r.image_id.includes(q)) &&
      ($("statusFilter").value === "all" ||
        r.status === $("statusFilter").value) &&
      ($("predictionFilter").value === "all" ||
        ($("predictionFilter").value === "zero"
          ? r.candidate_count === 0
          : r.candidate_count > 0)) &&
      ($("batchFilter").value === "all" || r.batch === $("batchFilter").value),
  );
  renderQueue();
  statusCounts();
}
function renderQueue() {
  const list = state.filtered.slice(0, state.limit);
  $("queueCount").textContent = state.filtered.length;
  $("queue").innerHTML = list.length
    ? list
        .map(
          (r) =>
            `<button class="queue-item ${r.image_id === state.id ? "current" : ""}" role="option" aria-selected="${r.image_id === state.id}" data-image="${r.image_id}"><img loading="lazy" src="/api/images/${r.image_id}/png" alt="${r.image_id}"><span><strong>${r.image_id}</strong><small>${t(r.status)} · Z8 ${r.candidate_count}${r.claimed_by ? " · " + esc(r.claimed_by.kind) : ""}</small></span><i class="status-dot ${r.status}"></i></button>`,
        )
        .join("")
    : `<div class="empty-labels">${t("noMatches")}</div>`;
  $("moreQueue").classList.toggle(
    "hidden",
    state.limit >= state.filtered.length,
  );
  if (state.id) {
    $("position").textContent =
      `${state.rows.findIndex((r) => r.image_id === state.id) + 1} / ${state.rows.length}`;
  }
}
function notice(message, buttons = []) {
  const el = $("notice");
  el.innerHTML = `<span>${esc(message)}</span>`;
  for (const [label, fn] of buttons) {
    const b = document.createElement("button");
    b.textContent = label;
    b.onclick = fn;
    el.appendChild(b);
  }
  el.classList.remove("hidden");
}
function clearNotice() {
  $("notice").classList.add("hidden");
  $("notice").textContent = "";
}
function recoveryKey() {
  return "fba-draft-" + state.id;
}
function persistLocal() {
  if (!state.a) return;
  try {
    localStorage.setItem(
      recoveryKey(),
      JSON.stringify({
        image_id: state.id,
        revision: state.rev,
        annotation: state.a,
        at: new Date().toISOString(),
      }),
    );
  } catch (e) {
    toast(
      state.lang === "zh"
        ? "本机草稿缓存失败，请及时保存或导出。"
        : "Local draft cache failed. Save or export now.",
      true,
    );
  }
}
function download(value, name, type = "application/json") {
  const blob =
    value instanceof Blob
      ? value
      : new Blob(
          [typeof value === "string" ? value : JSON.stringify(value, null, 2)],
          { type },
        );
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function downloadDraft() {
  download(
    { image_id: state.id, revision: state.rev, annotation: state.a },
    state.id + "-local-draft.json",
  );
}
async function loadImage(id, { skipFlush = false } = {}) {
  if (state.transition) return;
  state.transition = true;
  try {
    if (!skipFlush) await flush();
    const token = ++state.loadToken;
    const [record, meta] = await Promise.all([
      api("/api/annotations/" + id),
      api("/api/images/" + id),
    ]);
    if (token !== state.loadToken) return;
    state.id = id;
    state.record = record;
    state.meta = meta;
    state.a = clone(record.annotation);
    state.rev = record.revision;
    state.dirty = false;
    state.blocked = false;
    state.undo = [];
    state.redo = [];
    state.selected = null;
    state.birdId = state.a.instances?.[0]?.instance_id || null;
    state.predSelected = null;
    state.serial++;
    clearNotice();
    $("imageTitle").textContent = id;
    $("imageMeta").textContent =
      `384 × 256 · RGB · ${meta.batch.replace("community-images-2026-10-24-", "")}`;
    $("predCount").textContent = meta.predictions.length;
    $("emptyState").textContent = t("loading");
    $("emptyState").classList.remove("hidden");
    $("canvasImage").setAttribute("href", `/api/images/${id}/png`);
    fit();
    setTool("select");
    renderQueue();
    renderShapes();
    renderProperties();
    connection("saved");
    localStorage.setItem("fba-last-image", id);
    const saved = localStorage.getItem(recoveryKey());
    if (saved) {
      let draft;
      try {
        draft = JSON.parse(saved);
      } catch {}
      if (
        draft &&
        JSON.stringify(draft.annotation) !== JSON.stringify(record.annotation)
      ) {
        notice(t("recovery"), [
          [
            t("recover"),
            () => {
              if (draft.revision !== state.rev) {
                state.blocked = true;
                showConflict();
                return;
              }
              action(() => {
                state.a = clone(draft.annotation);
              });
              clearNotice();
            },
          ],
          [
            t("downloadDraft"),
            () => download(draft, id + "-recovered-draft.json"),
          ],
        ]);
      }
    }
  } catch (e) {
    showError(e);
  } finally {
    state.transition = false;
  }
}
$("canvasImage").addEventListener("load", () =>
  $("emptyState").classList.add("hidden"),
);
$("canvasImage").addEventListener("error", () => {
  $("emptyState").textContent = t("loadError");
  $("emptyState").classList.remove("hidden");
});
function showError(e) {
  if (e.status === 409) {
    state.blocked = true;
    persistLocal();
    showConflict();
    return;
  }
  let msg = e.message;
  if (Array.isArray(e.details))
    msg =
      t("validation") +
      ": " +
      e.details
        .filter((i) => i.severity === "error")
        .map((i) => (i.instance_id ? i.instance_id + " " : "") + t(i.code))
        .join("；");
  toast(msg, true);
}
function showConflict() {
  connection("conflict");
  notice(t("conflictHelp"), [
    [t("downloadDraft"), downloadDraft],
    [
      t("latest"),
      async () => {
        downloadDraft();
        localStorage.removeItem(recoveryKey());
        state.dirty = false;
        state.blocked = false;
        await loadImage(state.id, { skipFlush: true });
      },
    ],
  ]);
}
function prepareDraft() {
  if (state.a.instances === null) state.a.instances = [];
  if (state.a.uncertain_regions === null) state.a.uncertain_regions = [];
  state.a.annotation_status = "draft";
  state.a.review = null;
}
function touch({ right = true, draft = true } = {}) {
  if (draft) prepareDraft();
  state.dirty = true;
  state.serial++;
  persistLocal();
  connection(state.blocked ? "conflict" : "unsaved");
  renderShapes();
  if (right) renderProperties();
  else {
    const label = document.querySelector(".status-card>span");
    if (label) label.textContent = t(state.a.annotation_status);
    $("reviewButton").disabled =
      state.a.annotation_status !== "annotated" || who().kind === "ai";
    document.querySelectorAll(".review-summary").forEach((el) => el.remove());
  }
  clearTimeout(state.timer);
  if (!state.blocked)
    state.timer = setTimeout(() => flush().catch(showError), 650);
}
function action(fn, opts = {}) {
  if (!state.a || state.blocked) {
    if (state.blocked) showConflict();
    return;
  }
  state.undo.push(clone(state.a));
  if (state.undo.length > 100) state.undo.shift();
  state.redo = [];
  fn();
  touch(opts);
}
async function flush() {
  clearTimeout(state.timer);
  if (state.saving) {
    await state.saving;
    if (state.dirty) return flush();
    return;
  }
  if (!state.dirty || !state.a) return;
  if (state.blocked) {
    showConflict();
    throw new Error(t("conflict"));
  }
  const id = state.id,
    snapshot = clone(state.a),
    serial = state.serial,
    revision = state.rev;
  connection("saving");
  const task = (async () => {
    const result = await api("/api/annotations/" + id, "PUT", {
      base_revision: revision,
      annotation: snapshot,
      actor: who(),
    });
    if (state.id === id) {
      state.rev = result.revision;
      state.record = result;
      if (state.serial === serial) {
        state.a = clone(result.annotation);
        state.dirty = false;
        localStorage.removeItem(recoveryKey());
      } else {
        state.a.provenance = result.annotation.provenance;
        persistLocal();
      }
      const row = state.rows.find((r) => r.image_id === id);
      if (row)
        Object.assign(row, {
          revision: result.revision,
          status: result.annotation.annotation_status,
          presence: result.annotation.presence,
          decision: result.annotation.review_decision,
          bird_count: result.annotation.instances?.length || 0,
        });
      statusCounts();
      renderQueue();
      $("revision").textContent = "r" + state.rev;
      const contentActor = result.annotation.provenance.content_actor;
      let source = document.querySelector(".content-source");
      if (!source) {
        source = document.createElement("div");
        source.className = "tiny-help content-source";
        document.querySelector(".property-section")?.appendChild(source);
      }
      source.textContent =
        t("owner") + ": " + contentActor.id + " · " + t(contentActor.kind);
      connection(state.dirty ? "unsaved" : "saved");
      if (result.issues?.length) showIssues(result.issues);
    }
  })();
  state.saving = task;
  try {
    await task;
  } catch (e) {
    if (e.status === 409) {
      state.blocked = true;
      showConflict();
    } else connection("offline");
    throw e;
  } finally {
    state.saving = null;
  }
  if (state.dirty && !state.blocked) return flush();
}
function showIssues(issues) {
  const relevant = issues.filter((i) => i.severity === "warning");
  if (relevant.length)
    toast(
      relevant.map((i) => (i.instance_id || "") + " " + t(i.code)).join(" · "),
    );
}
function undo() {
  if (!state.undo.length || state.blocked) return;
  state.redo.push(clone(state.a));
  state.a = state.undo.pop();
  state.selected = null;
  touch();
}
function redo() {
  if (!state.redo.length || state.blocked) return;
  state.undo.push(clone(state.a));
  state.a = state.redo.pop();
  state.selected = null;
  touch();
}
function bird() {
  return state.a?.instances?.find((b) => b.instance_id === state.birdId);
}
function nextId(items, key, prefix) {
  const minimum =
    Math.max(
      0,
      ...items.map((x) => Number(String(x[key]).slice(prefix.length)) || 0),
    ) + 1;
  state.a.id_counters ||= {};
  const field = { b: "bird", u: "uncertain", e: "eye" }[prefix] || prefix;
  const n = Math.max(minimum, state.a.id_counters[field] || 1);
  state.a.id_counters[field] = n + 1;
  return prefix + n;
}
function newBird(box = null) {
  if (!state.a.instances) state.a.instances = [];
  const existing = bird();
  if (box && existing && !existing.bird_bbox_xyxy) {
    existing.bird_bbox_xyxy = box;
    existing.part_visibility.bird = "visible";
    state.a.presence = "present";
    deriveTarget(existing);
    state.selected = existing.instance_id + ":bird";
    return existing;
  }
  const b = {
    instance_id: nextId(state.a.instances, "instance_id", "b"),
    bird_bbox_xyxy: box,
    head_bbox_xyxy: null,
    eyes: [],
    part_visibility: {
      bird: box ? "visible" : "unknown",
      head: "unknown",
      eye: "unknown",
    },
    invisibility_reasons: [],
    occluder_types: [],
    occluded_parts: [],
    af_reference_target_input: box ? "body" : "unknown",
    af_anchor_input_xy: null,
    target_mode: "auto",
    anchor_mode: "manual",
    needs_review: false,
    notes: "",
  };
  state.a.instances.push(b);
  state.a.presence = "present";
  state.birdId = b.instance_id;
  state.selected = b.instance_id + ":bird";
  return b;
}
function deriveTarget(b) {
  const previousTarget = b.af_reference_target_input;
  if (b.target_mode !== "manual") {
    b.af_reference_target_input = b.eyes.length
      ? "eye"
      : b.head_bbox_xyxy
        ? "head"
        : b.bird_bbox_xyxy
          ? "body"
          : "unknown";
    if (
      b.eyes.length &&
      (previousTarget !== "eye" ||
        b.anchor_mode === "auto" ||
        !b.af_anchor_input_xy)
    ) {
      b.af_anchor_input_xy = clone(b.eyes[0].center_xy);
      b.anchor_mode = "auto";
    } else if (
      !b.eyes.length &&
      (b.anchor_mode === "auto" ||
        previousTarget !== b.af_reference_target_input)
    ) {
      b.af_anchor_input_xy = null;
      b.anchor_mode = "manual";
    }
  }
  if (["none", "unknown"].includes(b.af_reference_target_input))
    b.af_anchor_input_xy = null;
}
function addEye(b, p, bbox = null) {
  if (b.eyes.length >= 2) {
    toast(t("twoEyes"), true);
    return false;
  }
  const eye = {
    eye_id: nextId(b.eyes, "eye_id", "e"),
    center_xy: p,
    bbox_xyxy: bbox,
    side: "unknown",
  };
  b.eyes.push(eye);
  b.part_visibility.eye = "visible";
  state.selected = `${b.instance_id}:eye:${eye.eye_id}`;
  deriveTarget(b);
  return true;
}
function allShapes() {
  const shapes = [];
  for (const b of state.a?.instances || []) {
    if (b.bird_bbox_xyxy)
      shapes.push({
        key: b.instance_id + ":bird",
        kind: "bird",
        box: b.bird_bbox_xyxy,
        bird: b,
      });
    if (b.head_bbox_xyxy)
      shapes.push({
        key: b.instance_id + ":head",
        kind: "head",
        box: b.head_bbox_xyxy,
        bird: b,
      });
    for (const e of b.eyes) {
      if (e.bbox_xyxy)
        shapes.push({
          key: `${b.instance_id}:eyeBox:${e.eye_id}`,
          kind: "eye",
          box: e.bbox_xyxy,
          bird: b,
          eye: e,
        });
      shapes.push({
        key: `${b.instance_id}:eye:${e.eye_id}`,
        kind: "eye",
        point: e.center_xy,
        bird: b,
        eye: e,
      });
    }
    if (b.af_anchor_input_xy)
      shapes.push({
        key: b.instance_id + ":anchor",
        kind: "anchor",
        point: b.af_anchor_input_xy,
        bird: b,
      });
  }
  for (const u of state.a?.uncertain_regions || [])
    shapes.push({
      key: "uncertain:" + u.region_id,
      kind: "uncertain",
      box: u.bbox_xyxy,
      region: u,
    });
  return shapes;
}
function shape() {
  return allShapes().find((s) => s.key === state.selected);
}
function selectShape(key) {
  state.selected = key;
  const s = shape();
  if (s?.bird) state.birdId = s.bird.instance_id;
  renderShapes();
  renderProperties();
}
function setGeometry(s, geom) {
  if (s.box) {
    if (s.region) s.region.bbox_xyxy = geom;
    else if (s.eye) s.eye.bbox_xyxy = geom;
    else if (s.kind === "bird") s.bird.bird_bbox_xyxy = geom;
    else s.bird.head_bbox_xyxy = geom;
  } else if (s.kind === "eye") {
    s.eye.center_xy = geom;
    if (s.bird.anchor_mode === "auto" && s.bird.eyes[0] === s.eye)
      s.bird.af_anchor_input_xy = clone(geom);
  } else {
    s.bird.af_anchor_input_xy = geom;
    s.bird.anchor_mode = "manual";
  }
}
function removeSelected() {
  const s = shape();
  if (!s) {
    toast(t("noSelection"));
    return;
  }
  action(() => {
    if (s.region)
      state.a.uncertain_regions = state.a.uncertain_regions.filter(
        (u) => u !== s.region,
      );
    else if (s.key.includes(":eyeBox:")) s.eye.bbox_xyxy = null;
    else if (s.kind === "eye") {
      s.bird.eyes = s.bird.eyes.filter((e) => e !== s.eye);
      deriveTarget(s.bird);
    } else if (s.kind === "anchor") s.bird.af_anchor_input_xy = null;
    else if (s.kind === "head") {
      s.bird.head_bbox_xyxy = null;
      s.bird.part_visibility.head = "unknown";
      deriveTarget(s.bird);
    } else {
      s.bird.bird_bbox_xyxy = null;
      s.bird.part_visibility.bird = "unknown";
      deriveTarget(s.bird);
    }
    state.selected = null;
  });
  toast(t("deleted"));
}
function svgEl(tag, attrs, parent, text) {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  parent.appendChild(e);
  return e;
}
function screenScale() {
  const m = $("canvas").getScreenCTM();
  return m ? Math.abs(m.a) : 1;
}
function renderShapes() {
  if (!state.a) return;
  const g = $("shapes");
  g.replaceChildren();
  $("undo").disabled = !state.undo.length;
  $("redo").disabled = !state.redo.length;
  $("revision").textContent = "r" + state.rev;
  if ($("showLabels").checked) {
    const scale = screenScale();
    const labelSize = 11 / scale;
    for (const s of allShapes()) {
      const color = palette[s.kind],
        selected = state.selected === s.key;
      const group = svgEl("g", { "data-key": s.key, class: "shape" }, g);
      if (s.box) {
        const [x1, y1, x2, y2] = s.box;
        svgEl(
          "rect",
          {
            x: x1,
            y: y1,
            width: x2 - x1,
            height: y2 - y1,
            fill: selected ? color + "16" : "transparent",
            stroke: color,
            "stroke-width": selected ? 2.5 : 1.6,
            "vector-effect": "non-scaling-stroke",
            "stroke-dasharray": s.region ? "5 3" : "",
          },
          group,
        );
        svgEl(
          "text",
          {
            x: x1 + 2 / scale,
            y: Math.max(labelSize, y1 - 3 / scale),
            fill: color,
            "font-size": labelSize,
            "paint-order": "stroke",
            stroke: "#111820",
            "stroke-width": 3 / scale,
            "pointer-events": "none",
          },
          group,
          (s.bird?.instance_id || s.region?.region_id) +
            " " +
            (s.key.includes("eyeBox") ? t("eyeBoxMode") : t(s.kind)),
        );
        if (selected && state.tool === "select")
          for (const [i, [x, y]] of [
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2],
          ].entries())
            svgEl(
              "rect",
              {
                x: x - 3.5 / scale,
                y: y - 3.5 / scale,
                width: 7 / scale,
                height: 7 / scale,
                fill: color,
                stroke: "#131920",
                "stroke-width": 1,
                "vector-effect": "non-scaling-stroke",
                "data-handle": i,
                "data-key": s.key,
              },
              group,
            );
      } else {
        const [x, y] = s.point;
        if (s.kind === "anchor") {
          svgEl(
            "circle",
            {
              cx: x,
              cy: y,
              r: 7 / scale,
              fill: "transparent",
              stroke: color,
              "stroke-width": 1.5,
              "vector-effect": "non-scaling-stroke",
            },
            group,
          );
          svgEl(
            "path",
            {
              d: `M${x - 11 / scale},${y}h${22 / scale}M${x},${y - 11 / scale}v${22 / scale}`,
              stroke: color,
              "stroke-width": 1,
              "vector-effect": "non-scaling-stroke",
              "pointer-events": "none",
            },
            group,
          );
        } else {
          svgEl(
            "circle",
            {
              cx: x,
              cy: y,
              r: (selected ? 5 : 3.5) / scale,
              fill: color,
              stroke: "#152331",
              "stroke-width": 1.3,
              "vector-effect": "non-scaling-stroke",
            },
            group,
          );
          svgEl(
            "circle",
            { cx: x, cy: y, r: 10 / scale, fill: "transparent" },
            group,
          );
        }
      }
    }
  }
  renderPredictions();
}
function renderPredictions() {
  const g = $("predictions");
  g.replaceChildren();
  if (!$("showPredictions").checked || !state.meta) return;
  const scale = screenScale();
  state.meta.predictions.forEach((p, i) => {
    const [x1, y1, x2, y2] = p.box_input_xyxy;
    const selected = state.predSelected === i;
    const group = svgEl("g", { "data-pred": i, class: "pred" }, g);
    svgEl(
      "rect",
      {
        x: x1,
        y: y1,
        width: x2 - x1,
        height: y2 - y1,
        fill: selected ? "#ffffff12" : "transparent",
        stroke: slotColors[p.class_slot],
        "stroke-width": selected ? 2 : 1,
        "stroke-dasharray": "4 3",
        "vector-effect": "non-scaling-stroke",
        opacity: 0.8,
      },
      group,
    );
    svgEl(
      "text",
      {
        x: x1,
        y: y1 + 10 / scale,
        fill: slotColors[p.class_slot],
        "font-size": 10 / scale,
        "paint-order": "stroke",
        stroke: "#10151b",
        "stroke-width": 2 / scale,
        "pointer-events": "none",
      },
      group,
      `s${p.class_slot} / ${p.native_integer_score}`,
    );
  });
}
function updateView() {
  const v = state.view;
  $("canvas").setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
  $("zoomValue").textContent = Math.round(screenScale() * 100) + "%";
  renderShapes();
}
function fit() {
  state.view = { x: 0, y: 0, w: 384, h: 256 };
  updateView();
}
function zoom(
  factor,
  p = {
    x: state.view.x + state.view.w / 2,
    y: state.view.y + state.view.h / 2,
  },
) {
  const v = state.view,
    w = Math.min(768, Math.max(24, v.w / factor)),
    ratio = w / v.w;
  state.view = {
    x: p.x - (p.x - v.x) * ratio,
    y: p.y - (p.y - v.y) * ratio,
    w,
    h: (w * 2) / 3,
  };
  updateView();
}
function pointer(event) {
  const p = $("canvas").createSVGPoint();
  p.x = event.clientX;
  p.y = event.clientY;
  const m = $("canvas").getScreenCTM();
  const v = p.matrixTransform(m.inverse());
  return { x: v.x, y: v.y };
}
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function coord(p) {
  return [
    +clamp(p.x, 0, 383.999).toFixed(3),
    +clamp(p.y, 0, 255.999).toFixed(3),
  ];
}
function setTool(tool) {
  state.tool = tool;
  const keys = {
    select: "V",
    bird: "B",
    head: "H",
    eye: "E",
    anchor: "P",
    uncertain: "U",
  };
  document.querySelectorAll("[data-tool]").forEach((b) => {
    b.classList.toggle("active", b.dataset.tool === tool);
    b.setAttribute(
      "aria-label",
      t(b.dataset.tool) + " (" + keys[b.dataset.tool] + ")",
    );
    b.title = t(b.dataset.tool) + " · " + keys[b.dataset.tool];
  });
  $("canvas").classList.toggle("drawing", tool !== "select");
  $("toolHint").textContent = t(
    tool === "eyeBox" ? "eyeBoxHint" : tool + "Hint",
  );
  $("preview").replaceChildren();
}
function drawPreview(a, b) {
  const g = $("preview");
  g.replaceChildren();
  svgEl(
    "rect",
    {
      x: Math.min(a.x, b.x),
      y: Math.min(a.y, b.y),
      width: Math.abs(b.x - a.x),
      height: Math.abs(b.y - a.y),
      fill: "#e4b46b12",
      stroke: palette[state.tool] || palette.eye,
      "stroke-width": 1.5,
      "stroke-dasharray": "4 2",
      "vector-effect": "non-scaling-stroke",
    },
    g,
  );
}
function gestureStart(event) {
  if ((event.button !== 0 && event.button !== 1) || !state.a || state.blocked)
    return;
  const p = pointer(event);
  if (state.space || event.button === 1) {
    state.gesture = {
      type: "pan",
      start: p,
      client: [event.clientX, event.clientY],
      view: clone(state.view),
      scale: screenScale(),
    };
    $("canvas").setPointerCapture(event.pointerId);
    event.preventDefault();
    return;
  }
  if (p.x < 0 || p.x >= 384 || p.y < 0 || p.y >= 256) return;
  if (state.tool === "select") {
    const target = event.target.closest("[data-key]");
    const pred = event.target.closest("[data-pred]");
    if (target) {
      selectShape(target.dataset.key);
      const s = shape();
      state.gesture = {
        type: target.hasAttribute("data-handle") ? "resize" : "move",
        start: p,
        key: s.key,
        geometry: clone(s.box || s.point),
        handle: Number(target.dataset.handle),
        before: clone(state.a),
        changed: false,
      };
      $("canvas").setPointerCapture(event.pointerId);
    } else if (pred) {
      state.predSelected = Number(pred.dataset.pred);
      renderPredictions();
      renderProperties();
    } else {
      state.selected = null;
      renderShapes();
      renderProperties();
    }
    return;
  }
  if (["head", "eye", "anchor", "eyeBox"].includes(state.tool) && !bird()) {
    toast(t("selectBird"), true);
    return;
  }
  if (state.tool === "eye") {
    if (bird().eyes.length >= 2) {
      toast(t("twoEyes"), true);
      return;
    }
    action(() => addEye(bird(), coord(p)));
    return;
  }
  if (state.tool === "anchor") {
    action(() => {
      const b = bird();
      b.af_anchor_input_xy = coord(p);
      b.anchor_mode = "manual";
      if (["none", "unknown"].includes(b.af_reference_target_input)) {
        b.target_mode = "auto";
        deriveTarget(b);
      }
    });
    return;
  }
  state.gesture = { type: "draw", start: p, tool: state.tool };
  $("canvas").setPointerCapture(event.pointerId);
  event.preventDefault();
}
function gestureMove(event) {
  if (!state.a) return;
  const p = pointer(event);
  $("cursorPosition").textContent = `x ${p.x.toFixed(1)} · y ${p.y.toFixed(1)}`;
  const g = state.gesture;
  if (!g) return;
  if (g.type === "pan") {
    state.view.x = g.view.x - (event.clientX - g.client[0]) / g.scale;
    state.view.y = g.view.y - (event.clientY - g.client[1]) / g.scale;
    updateView();
    return;
  }
  if (g.type === "draw") {
    drawPreview(g.start, { x: clamp(p.x, 0, 384), y: clamp(p.y, 0, 256) });
    return;
  }
  const s = allShapes().find((s) => s.key === g.key);
  if (!s) return;
  const dx = p.x - g.start.x,
    dy = p.y - g.start.y;
  if (Math.abs(dx) + Math.abs(dy) < 0.1) return;
  let geom = clone(g.geometry);
  if (g.type === "move") {
    if (geom.length === 4) {
      const mx = clamp(dx, -geom[0], 384 - geom[2]),
        my = clamp(dy, -geom[1], 256 - geom[3]);
      geom = [geom[0] + mx, geom[1] + my, geom[2] + mx, geom[3] + my];
    } else {
      geom = [clamp(geom[0] + dx, 0, 383.999), clamp(geom[1] + dy, 0, 255.999)];
    }
  } else {
    const x = clamp(p.x, 0, 384),
      y = clamp(p.y, 0, 256);
    if ([0, 3].includes(g.handle)) geom[0] = Math.min(x, geom[2] - 0.2);
    else geom[2] = Math.max(x, geom[0] + 0.2);
    if ([0, 1].includes(g.handle)) geom[1] = Math.min(y, geom[3] - 0.2);
    else geom[3] = Math.max(y, geom[1] + 0.2);
  }
  setGeometry(
    s,
    geom.map((x) => +x.toFixed(3)),
  );
  g.changed = true;
  renderShapes();
}
function gestureEnd(event) {
  const g = state.gesture;
  if (!g) return;
  state.gesture = null;
  $("preview").replaceChildren();
  if ($("canvas").hasPointerCapture(event.pointerId))
    $("canvas").releasePointerCapture(event.pointerId);
  if (g.type === "pan") return;
  if (g.type !== "draw") {
    if (g.changed) {
      state.undo.push(g.before);
      state.redo = [];
      touch();
    }
    return;
  }
  const p = pointer(event),
    x1 = clamp(Math.min(g.start.x, p.x), 0, 384),
    x2 = clamp(Math.max(g.start.x, p.x), 0, 384),
    y1 = clamp(Math.min(g.start.y, p.y), 0, 256),
    y2 = clamp(Math.max(g.start.y, p.y), 0, 256);
  if (x2 - x1 < 0.6 || y2 - y1 < 0.6) {
    toast(t("smallBox"));
    return;
  }
  const box = [x1, y1, x2, y2].map((x) => +x.toFixed(3));
  action(() => {
    if (g.tool === "bird") newBird(box);
    else if (g.tool === "head") {
      const b = bird();
      b.head_bbox_xyxy = box;
      b.part_visibility.head = "visible";
      deriveTarget(b);
      state.selected = b.instance_id + ":head";
    } else if (g.tool === "uncertain") {
      if (!state.a.uncertain_regions) state.a.uncertain_regions = [];
      const u = {
        region_id: nextId(state.a.uncertain_regions, "region_id", "u"),
        bbox_xyxy: box,
        reason: "unknown",
        needs_review: true,
      };
      state.a.uncertain_regions.push(u);
      if (!state.a.instances?.length) state.a.presence = "uncertain";
      state.selected = "uncertain:" + u.region_id;
    } else if (g.tool === "eyeBox") {
      const s = shape();
      if (s?.eye) {
        if (
          s.eye.center_xy[0] < x1 ||
          s.eye.center_xy[0] >= x2 ||
          s.eye.center_xy[1] < y1 ||
          s.eye.center_xy[1] >= y2
        ) {
          toast(t("invalidCoords"), true);
          return;
        }
        s.eye.bbox_xyxy = box;
        state.selected = `${s.bird.instance_id}:eyeBox:${s.eye.eye_id}`;
      }
    }
  });
  if (g.tool === "eyeBox") setTool("select");
}
function renderProperties() {
  const panel = $("properties");
  if (!state.a) {
    panel.innerHTML = "";
    return;
  }
  const a = state.a,
    b = bird(),
    s = shape();
  let html = `<section class="property-section"><div class="status-card"><span>${t(a.annotation_status)}</span><span class="tag">${t("inputSpace")}</span></div>${a.provenance ? `<div class="tiny-help content-source">${t("owner")}: ${esc(a.provenance.content_actor?.id || a.provenance.actor.id)} · ${t(a.provenance.content_actor?.kind || a.provenance.actor.kind)}</div>` : ""}${a.review ? `<div class="tiny-help review-summary">${t(a.review.independent ? "independentReview" : "selfReview")} · ${esc(a.review.reviewer.id)}</div>` : ""}</section>`;
  html += `<section class="property-section"><div class="section-title"><h3>${t("birds")} <span class="counter">${a.instances?.length || 0}</span></h3><button class="quiet" data-action="newBird">${t("newBird")}</button></div><div class="bird-tabs">${(a.instances || []).map((x) => `<button class="bird-tab ${x.instance_id === state.birdId ? "selected" : ""}" data-select-bird="${x.instance_id}">${x.instance_id}<small>${t(x.af_reference_target_input + "Target")}</small></button>`).join("")}</div>${!(a.instances || []).length ? `<p class="empty-labels">${t("noLabels")}</p>` : ""}<div class="shape-list">${allShapes()
    .filter((x) => x.region || x.bird?.instance_id === state.birdId)
    .map(
      (x) =>
        `<button class="shape-row ${x.key === state.selected ? "selected" : ""}" data-shape="${x.key}"><i class="shape-icon" style="background:${palette[x.kind]}"></i>${esc(x.region?.region_id || x.eye?.eye_id || x.bird.instance_id)} · ${x.key.includes("eyeBox") ? t("eyeBoxMode") : t(x.kind)}<small>${x.box ? x.box.map((n) => n.toFixed(1)).join(", ") : x.point.map((n) => n.toFixed(1)).join(", ")}</small></button>`,
    )
    .join("")}</div></section>`;
  if (s) {
    const values = s.box || s.point;
    html += `<section class="property-section"><div class="section-title"><h3>${t("geometry")}</h3><button class="quiet" data-action="delete">${t("delete")}</button></div><div class="coord-grid">${values.map((n, i) => `<label>${values.length === 4 ? ["x₁", "y₁", "x₂", "y₂"][i] : ["x", "y"][i]}<input type="number" step="any" data-coord="${i}" value="${+n.toFixed(3)}" aria-label="${values.length === 4 ? ["x1", "y1", "x2", "y2"][i] : ["x", "y"][i]}"></label>`).join("")}</div>${
      s.eye
        ? `<div class="eye-options"><select data-field="eyeSide" aria-label="${t("side")}">${options(
            [
              ["unknown", t("unknownSide")],
              ["left", t("left")],
              ["right", t("right")],
            ],
            s.eye.side,
          )}</select><button data-action="eyeBox">${t("eyeBox")}</button></div>${s.eye.bbox_xyxy ? `<button class="quiet" data-action="removeEyeBox">${t("noEyeBox")}</button>` : ""}`
        : ""
    }</section>`;
  }
  if (s?.region) {
    html += `<section class="property-section"><label class="property-label">${state.lang === "zh" ? "疑似原因" : "Why uncertain"}</label><textarea data-field="regionNotes" aria-label="${state.lang === "zh" ? "疑似原因" : "Why uncertain"}">${esc(s.region.reason)}</textarea></section>`;
  }
  if (b) {
    html += `<section class="property-section"><h3>${t("target")}</h3><select data-field="target" aria-label="${t("target")}" style="margin-top:8px">${options([["auto", t("auto")], ...["eye", "head", "body", "none", "unknown"].map((x) => [x, t(x + "Target")])], b.target_mode === "manual" ? b.af_reference_target_input : "auto")}</select><div class="anchor-summary"><span>${t(b.af_reference_target_input + "Target")}</span><span>${b.af_anchor_input_xy ? b.af_anchor_input_xy.map((x) => x.toFixed(1)).join(", ") : "—"}</span></div>${!b.af_anchor_input_xy && !["none", "unknown"].includes(b.af_reference_target_input) ? `<div class="warning">${t("anchorNeeded")}</div>` : ""}<h3 style="margin:13px 0 8px">${t("visibility")}</h3><div class="visibility-grid">${[
      "bird",
      "head",
      "eye",
    ]
      .map(
        (p) =>
          `<span>${t(p)}</span><select data-visibility="${p}" aria-label="${t(p)} ${t("visibility")}">${options(
            ["visible", "partial", "hidden", "out_of_frame", "unknown"].map(
              (x) => [x, t(x)],
            ),
            b.part_visibility[p],
          )}</select>`,
      )
      .join(
        "",
      )}</div><label class="property-label">${t("occluders")}</label><div class="chips">${["branch", "leaf", "dense_foliage", "trunk", "grass", "other_bird", "other", "unknown"].map((v) => `<button class="chip ${b.occluder_types.includes(v) ? "on" : ""}" data-chip="occluder_types:${v}">${t(v)}</button>`).join("")}</div><label class="property-label">${t("reasons")}</label><div class="chips">${["occlusion", "pose", "defocus", "motion_blur", "too_small", "compression", "out_of_frame", "unknown"].map((v) => `<button class="chip ${b.invisibility_reasons.includes(v) ? "on" : ""}" data-chip="invisibility_reasons:${v}">${t(v)}</button>`).join("")}</div><label class="property-label">${state.lang === "zh" ? "被遮挡部位" : "Occluded parts"}</label><div class="chips">${["bird", "head", "eye"].map((v) => `<button class="chip ${b.occluded_parts.includes(v) ? "on" : ""}" data-chip="occluded_parts:${v}">${t(v)}</button>`).join("")}</div><label class="property-label">${t("birdNotes")}</label><textarea data-field="birdNotes" aria-label="${t("birdNotes")}">${esc(b.notes)}</textarea><button class="quiet" data-action="deleteBird">${t("deleteBird")}</button></section>`;
  }
  html += `<section class="property-section"><h3>${t("decision")}</h3><select data-field="decision" aria-label="${t("decision")}" style="margin-top:8px">${options(
    ["unassessed", "reasonable", "error", "uncertain"].map((x) => [
      x,
      t(x === "uncertain" ? "uncertainDecision" : x),
    ]),
    a.review_decision,
  )}</select><p class="tiny-help">${t("decisionHelp")}</p><label class="property-label">${t("notes")}</label><textarea data-field="notes" aria-label="${t("notes")}">${esc(a.notes)}</textarea>${a.reference_consulted ? `<p class="reference-badge">${t("referenceViewed")}</p>` : ""}</section>`;
  if ($("showPredictions").checked) {
    html += `<section class="property-section"><h3>${t("rawPred")}</h3><p class="tiny-help" style="margin-bottom:8px">${t("predHelp")}</p>${state.meta.predictions.map((p, i) => `<div class="pred-row ${state.predSelected === i ? "selected" : ""}" data-pred-row="${i}"><span style="color:${slotColors[p.class_slot]}">slot ${p.class_slot}</span> / ${p.native_integer_score}<div class="pred-actions"><button data-adopt="${i}:bird">${t("adoptBird")}</button><button data-adopt="${i}:head">${t("adoptHead")}</button><button data-adopt="${i}:eye">${t("adoptEye")}</button></div></div>`).join("") || `<p class="tiny-help">${t("noPred")}</p>`}</section>`;
  }
  panel.innerHTML = html;
  $("reviewButton").disabled =
    a.annotation_status !== "annotated" || who().kind === "ai";
  $("referenceButton").disabled = !state.meta.reference.available;
}
function adopt(index, kind) {
  const p = state.meta.predictions[index],
    box = p.box_input_xyxy.map((x, i) => clamp(x, 0, i % 2 ? 256 : 384));
  if (box[2] <= box[0] || box[3] <= box[1]) return;
  if (kind !== "bird" && !bird()) {
    toast(t("selectBird"), true);
    return;
  }
  if (kind === "eye" && bird().eyes.length >= 2) {
    toast(t("twoEyes"), true);
    return;
  }
  action(() => {
    if (kind === "bird") newBird(box);
    else if (kind === "head") {
      bird().head_bbox_xyxy = box;
      bird().part_visibility.head = "visible";
      deriveTarget(bird());
      state.selected = bird().instance_id + ":head";
    } else addEye(bird(), [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]);
  });
}
function dialog(title, body) {
  $("dialogTitle").textContent = title;
  $("dialogBody").className = "dialog-content";
  $("dialogBody").innerHTML = body;
  $("dialog").showModal();
}
async function navigate(delta) {
  const ids = state.filtered.map((r) => r.image_id);
  const at = ids.indexOf(state.id),
    id = ids[at + delta];
  if (id) await loadImage(id);
  else toast(t("nextEnd"));
}
async function submit() {
  if (!state.a || state.blocked) return;
  try {
    await flush();
    if (
      !state.a.instances?.length &&
      !state.a.uncertain_regions?.length &&
      state.a.presence !== "absent"
    ) {
      toast(t("needPresence"), true);
      return;
    }
    const before = clone(state.a);
    prepareDraft();
    state.a.annotation_status = "annotated";
    if (state.a.instances?.length) state.a.presence = "present";
    else if (state.a.uncertain_regions?.length) state.a.presence = "uncertain";
    try {
      await api("/api/validate", "POST", {
        image_id: state.id,
        annotation: state.a,
      });
    } catch (e) {
      state.a = before;
      renderProperties();
      showError(e);
      return;
    }
    touch({ draft: false });
    await flush();
    renderProperties();
    toast(t("completeToast"));
    const ids = state.filtered.map((r) => r.image_id),
      idx = ids.indexOf(state.id);
    let next = ids
      .slice(idx + 1)
      .concat(ids.slice(0, idx))
      .find((id) =>
        ["pending", "draft", "needs_adjudication"].includes(
          state.rows.find((r) => r.image_id === id).status,
        ),
      );
    if (next) await loadImage(next);
    else toast(t("allDone"));
  } catch (e) {
    showError(e);
  }
}
async function markReviewed() {
  if (!state.a || state.blocked) return;
  if (who().kind === "ai") {
    toast(t("aiReview"), true);
    return;
  }
  try {
    await flush();
    if (state.a.annotation_status !== "annotated") {
      toast(t("validation"), true);
      return;
    }
    state.a.annotation_status = "reviewed";
    touch({ draft: false });
    await flush();
    renderProperties();
    toast(t("reviewToast"));
  } catch (e) {
    state.a.annotation_status = "annotated";
    renderProperties();
    showError(e);
  }
}
function exportDialog() {
  dialog(
    t("exportTitle"),
    `<p>${t("exportHelp")}</p><div class="actions"><button data-export-scope="all">${t("allExport")}</button><button data-export-scope="complete">${t("completeExport")}</button><button data-export-scope="reviewed">${t("reviewedExport")}</button></div><div class="actions"><button id="dialogImport">${t("import")}</button><button id="dialogBackup">${t("backup")}</button></div><p>${state.lang === "zh" ? "工作区中的 PNG、SQLite 数据库和修订历史保存在本地。数据库快照包含历史，可用于恢复。当前版本导出原生 JSONL，不自动转换为训练标签。" : "Input PNGs, SQLite labels and revision history stay in the local workspace. Database snapshots include history for recovery. Native JSONL is exported without automatic conversion to training labels."}</p>`,
  );
  document.querySelectorAll("[data-export-scope]").forEach(
    (b) =>
      (b.onclick = async () => {
        try {
          await flush();
          const response = await fetch(
            "/api/export?scope=" + b.dataset.exportScope,
          );
          if (!response.ok) throw new Error(await response.text());
          download(
            await response.blob(),
            `forest-bird-input-labels-${b.dataset.exportScope}.jsonl`,
          );
        } catch (e) {
          showError(e);
        }
      }),
  );
  $("dialogImport").onclick = () => $("importFile").click();
  $("dialogBackup").onclick = async () => {
    try {
      await flush();
      const r = await api("/api/backup", "POST", {});
      toast(t("backupDone") + ": " + r.file);
    } catch (e) {
      showError(e);
    }
  };
}
function helpDialog() {
  const zh = state.lang === "zh";
  dialog(
    t("helpTitle"),
    `<p>${zh ? "① B 画鸟框 → ② H 画头框 → ③ E 点可见眼。每只鸟关联自己的头和眼。眼不可见时不补眼；头／鸟身回退请用 P 指定可见参考点。" : "① B: bird box → ② H: head box → ③ E: visible eye center. Link parts to the same bird. Never guess a hidden eye. Use P to place a visible focus anchor for head/body fallback."}</p><table><tbody>${[
      ["B / H / E", "bird / head / eye"],
      ["P / U", "anchor / uncertain"],
      ["V", "select"],
      ["F", "fit"],
      ["Ctrl+Z / Ctrl+Shift+Z", zh ? "撤销 / 重做" : "Undo / redo"],
      ["Delete", zh ? "删除选中形状" : "Delete selection"],
      ["← / →", zh ? "上一张 / 下一张" : "Previous / next"],
      ["Enter", "complete"],
      ["Space + drag", zh ? "平移画面" : "Pan"],
      ["Mouse wheel", zh ? "以指针为中心缩放" : "Zoom at cursor"],
    ]
      .map(
        ([k, v]) =>
          `<tr><td><kbd>${k}</kbd></td><td>${esc(words[state.lang][v] || v)}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table><p>${zh ? "选中框可拖动，拖四角改大小；右侧坐标可精确输入。选中眼后可补可见眼框。自动保存到本地数据库，Ctrl+Z 的更改也会保存；修订历史不会被覆盖。" : "Move selected shapes or drag corners to resize. Edit exact coordinates in the details panel. Add an eye box only when its boundary is visible. Changes autosave to SQLite with immutable revision history."}</p><h3>${t("aiTitle")}</h3><pre>GET  /api/dataset\nGET  /api/images/fb_0008/png\nGET  /api/annotations/fb_0008\nPUT  /api/annotations/fb_0008\nPOST /api/claim\nGET  /api/help</pre><p>${zh ? "AI 使用 actor.kind=ai，读出 revision 后提交 base_revision。多人同时修改会返回 409，不覆盖他人的记录。AI 不能直接标记“已复核”。" : "AI identifies actor.kind=ai and submits the base_revision it read. Concurrent edits return 409 instead of overwriting. AI cannot mark records human-reviewed."}</p><p>${zh ? "此版本按你的要求标注 384×256 输入。查看原图只提供参考，原图上才看得见的眼，不能当作输入图也能看见。六个 slot 不直接变成人工类别。" : "This workspace annotates 384×256 input evidence. Original reference does not prove a part is visible in input pixels. Raw slots are not automatically converted into semantic ground truth."}</p>`,
  );
  $("dialogBody").insertAdjacentHTML(
    "afterbegin",
    `<div class="actions"><label>${state.lang === "zh" ? "标注者编号" : "Annotator ID"} <input id="dialogActorInput" value="${esc(who().id)}" maxlength="80"></label><button id="dialogActorSave">${state.lang === "zh" ? "保存标注者" : "Save annotator"}</button></div>`,
  );
  $("dialogActorInput").parentElement.insertAdjacentHTML(
    "afterend",
    `<label>${state.lang === "zh" ? "操作者类型" : "Operator type"} <select id="dialogActorKind" aria-label="Operator type">${options(
      [
        ["human", t("human")],
        ["ai", t("ai")],
      ],
      who().kind,
    )}</select></label>`,
  );
  $("dialogActorSave").onclick = async () => {
    try {
      await flush();
      const id = $("dialogActorInput").value.trim();
      if (!id)
        throw new Error(
          state.lang === "zh" ? "请输入标注者编号" : "Enter an annotator ID",
        );
      $("actor").value = id;
      localStorage.setItem("fba-actor", id);
      localStorage.setItem("fba-actor-kind", $("dialogActorKind").value);
      renderProperties();
      toast(state.lang === "zh" ? "标注者已更新" : "Annotator updated");
    } catch (e) {
      showError(e);
    }
  };
}
async function showHistory() {
  if (!state.id) return;
  try {
    await flush();
    const r = await api("/api/history/" + state.id);
    dialog(
      t("historyTitle"),
      r.history.length
        ? r.history
            .map(
              (h, i) =>
                `<div class="history-entry"><button data-restore="${i}">${t("restore")}</button><strong>r${h.revision}</strong> · ${esc(h.actor.id)} (${t(h.actor.kind)})<p>${esc(h.created)} · ${t(h.annotation.annotation_status)}</p></div>`,
            )
            .join("")
        : `<p>${t("noHistory")}</p>`,
    );
    document.querySelectorAll("[data-restore]").forEach(
      (b) =>
        (b.onclick = () => {
          action(() => {
            state.a = clone(r.history[Number(b.dataset.restore)].annotation);
            state.selected = null;
            state.birdId = state.a.instances?.[0]?.instance_id || null;
          });
          $("dialog").close();
          toast(t("restoreDone"));
        }),
    );
  } catch (e) {
    showError(e);
  }
}
async function showReference() {
  if (!state.meta?.reference.available) return;
  action(() => (state.a.reference_consulted = true), { right: false });
  dialog(
    t("reference"),
    `<p>${t("referenceHelp")}</p><img class="reference-image" src="/api/images/${state.id}/reference" alt="${state.id} original reference"><p>${state.meta.reference.width} × ${state.meta.reference.height} · ${state.id}</p>`,
  );
}
async function refreshDataset() {
  try {
    const result = await api("/api/dataset");
    state.rows = result.images;
    statusCounts();
    filterQueue();
    const current = state.rows.find((r) => r.image_id === state.id);
    if (current && current.revision > state.rev && !state.saving) {
      if (state.dirty) {
        state.blocked = true;
        showConflict();
      } else
        notice(t("remoteChange"), [[t("reload"), () => loadImage(state.id)]]);
    }
  } catch (e) {
    connection("offline");
  }
}

$("queue").addEventListener("click", (event) => {
  const b = event.target.closest("[data-image]");
  if (b) loadImage(b.dataset.image);
});
for (const id of ["search", "statusFilter", "predictionFilter", "batchFilter"])
  $(id).addEventListener(id === "search" ? "input" : "change", () => {
    state.limit = 60;
    filterQueue();
  });
$("moreQueue").onclick = () => {
  state.limit += 60;
  renderQueue();
};
$("language").onchange = () => {
  state.lang = $("language").value;
  localStorage.setItem("fba-language", state.lang);
  translate();
};
$("actor").value = localStorage.getItem("fba-actor") || "reviewer-local";
$("actor").onchange = () => localStorage.setItem("fba-actor", $("actor").value);
document
  .querySelectorAll("[data-tool]")
  .forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
$("showPredictions").onchange = () => {
  renderPredictions();
  renderProperties();
};
$("showLabels").onchange = renderShapes;
$("pixelated").onchange = () =>
  $("canvas").classList.toggle("pixelated", $("pixelated").checked);
$("canvas").classList.add("pixelated");
$("canvas").addEventListener("pointerdown", gestureStart);
$("canvas").addEventListener("pointermove", gestureMove);
$("canvas").addEventListener("pointerup", gestureEnd);
$("canvas").addEventListener("pointercancel", (event) => {
  const g = state.gesture;
  if (g?.before) {
    state.a = g.before;
    renderShapes();
  }
  state.gesture = null;
  $("preview").replaceChildren();
});
$("canvas").addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, pointer(event));
  },
  { passive: false },
);
$("zoomIn").onclick = () => zoom(1.3);
$("zoomOut").onclick = () => zoom(1 / 1.3);
$("fit").onclick = fit;
$("undo").onclick = undo;
$("redo").onclick = redo;
$("deleteShape").onclick = removeSelected;
$("previous").onclick = () => navigate(-1);
$("next").onclick = () => navigate(1);
$("saveButton").onclick = () =>
  flush()
    .then(() => toast(t("savedToast")))
    .catch(showError);
$("noBird").onclick = () => {
  if (state.a?.instances?.length || state.a?.uncertain_regions?.length) {
    toast(t("noBirdWithShapes"), true);
    return;
  }
  action(() => {
    state.a.instances = [];
    state.a.uncertain_regions = [];
    state.a.presence = "absent";
  });
  toast(t("noneConfirmed"));
};
$("discuss").onclick = () => {
  if (!state.a) return;
  action(
    () => {
      prepareDraft();
      state.a.annotation_status = "needs_adjudication";
    },
    { draft: false },
  );
};
$("completeButton").onclick = submit;
$("reviewButton").onclick = markReviewed;
$("helpButton").onclick = helpDialog;
$("exportButton").onclick = exportDialog;
$("historyButton").onclick = showHistory;
$("referenceButton").onclick = showReference;
$("closeDialog").onclick = () => $("dialog").close();
$("dialog").addEventListener("click", (event) => {
  if (event.target === $("dialog")) {
    const rect = $("dialog").getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      $("dialog").close();
  }
});
$("properties").addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.selectBird) {
    state.birdId = el.dataset.selectBird;
    state.selected = state.birdId + ":bird";
    renderShapes();
    renderProperties();
  } else if (el.dataset.shape) selectShape(el.dataset.shape);
  else if (el.dataset.chip) {
    const [field, value] = el.dataset.chip.split(":");
    action(() => {
      const b = bird();
      b[field] = b[field].includes(value)
        ? b[field].filter((v) => v !== value)
        : [...b[field], value];
    });
  } else if (el.dataset.adopt) {
    const [i, kind] = el.dataset.adopt.split(":");
    adopt(Number(i), kind);
  } else if (el.dataset.action === "newBird") {
    action(() => newBird());
    setTool("bird");
  } else if (el.dataset.action === "delete") removeSelected();
  else if (el.dataset.action === "deleteBird") {
    action(() => {
      state.a.instances = state.a.instances.filter(
        (x) => x.instance_id !== state.birdId,
      );
      state.birdId = state.a.instances[0]?.instance_id || null;
      state.selected = null;
      if (!state.a.instances.length)
        state.a.presence = state.a.uncertain_regions.length
          ? "uncertain"
          : null;
    });
  } else if (el.dataset.action === "eyeBox") {
    if (shape()?.eye) setTool("eyeBox");
  } else if (el.dataset.action === "removeEyeBox") {
    action(() => (shape().eye.bbox_xyxy = null));
  }
});
$("properties").addEventListener("change", (event) => {
  const el = event.target;
  if (el.hasAttribute("data-coord")) {
    const s = shape();
    if (!s) return;
    const geom = clone(s.box || s.point);
    geom[Number(el.dataset.coord)] = Number(el.value);
    const valid =
      geom.every(Number.isFinite) &&
      (s.box
        ? geom[0] >= 0 &&
          geom[1] >= 0 &&
          geom[2] <= 384 &&
          geom[3] <= 256 &&
          geom[0] < geom[2] &&
          geom[1] < geom[3]
        : geom[0] >= 0 && geom[0] < 384 && geom[1] >= 0 && geom[1] < 256);
    if (!valid) {
      toast(t("invalidCoords"), true);
      renderProperties();
      return;
    }
    if (JSON.stringify(geom) !== JSON.stringify(s.box || s.point))
      action(() => setGeometry(s, geom));
  } else if (el.dataset.visibility)
    action(() => (bird().part_visibility[el.dataset.visibility] = el.value));
  else if (el.dataset.field === "target")
    action(() => {
      const b = bird();
      b.target_mode = el.value === "auto" ? "auto" : "manual";
      if (el.value !== "auto") {
        if (b.af_reference_target_input !== el.value)
          b.af_anchor_input_xy = null;
        b.af_reference_target_input = el.value;
        if (el.value === "eye" && b.eyes.length) {
          b.af_anchor_input_xy = clone(b.eyes[0].center_xy);
          b.anchor_mode = "auto";
        }
      }
      deriveTarget(b);
    });
  else if (el.dataset.field === "eyeSide")
    action(() => (shape().eye.side = el.value));
  else if (el.dataset.field === "decision")
    action(() => (state.a.review_decision = el.value));
});
$("properties").addEventListener("input", (event) => {
  const el = event.target;
  if (el.hasAttribute("data-coord") && el.value !== "") {
    const s = shape();
    if (!s) return;
    const geom = clone(s.box || s.point);
    geom[Number(el.dataset.coord)] = Number(el.value);
    const valid =
      geom.every(Number.isFinite) &&
      (s.box
        ? geom[0] >= 0 &&
          geom[1] >= 0 &&
          geom[2] <= 384 &&
          geom[3] <= 256 &&
          geom[0] < geom[2] &&
          geom[1] < geom[3]
        : geom[0] >= 0 && geom[0] < 384 && geom[1] >= 0 && geom[1] < 256);
    if (valid && JSON.stringify(geom) !== JSON.stringify(s.box || s.point)) {
      action(() => setGeometry(s, geom), { right: false });
      const summary = document.querySelector(".shape-row.selected small");
      if (summary)
        summary.textContent = geom.map((x) => x.toFixed(1)).join(", ");
    }
    return;
  }
  if (["notes", "birdNotes", "regionNotes"].includes(el.dataset.field)) {
    action(
      () => {
        if (el.dataset.field === "notes") state.a.notes = el.value;
        else if (el.dataset.field === "regionNotes")
          shape().region.reason = el.value;
        else bird().notes = el.value;
      },
      { right: false },
    );
  }
});
$("importFile").onchange = async () => {
  const file = $("importFile").files[0];
  if (!file) return;
  try {
    await flush();
    const text = await file.text();
    let rows;
    try {
      const value = JSON.parse(text);
      rows = Array.isArray(value) ? value : [value];
    } catch {
      rows = text
        .split(/\r?\n/)
        .filter((x) => x.trim())
        .map((x) => JSON.parse(x));
    }
    if (!rows.length) throw new Error(t("importEmpty"));
    await api("/api/import", "POST", {
      actor: who(),
      records: rows.map((r) => ({
        image_id: r.image_id,
        base_revision: r.base_revision ?? r.revision,
        annotation: r.annotation,
      })),
    });
    $("dialog").close();
    state.dirty = false;
    await refreshDataset();
    await loadImage(state.id, { skipFlush: true });
    toast(t("importDone") + ": " + rows.length);
  } catch (e) {
    showError(e);
  } finally {
    $("importFile").value = "";
  }
};
document.addEventListener("keydown", (event) => {
  if ($("dialog").open) return;
  const editing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
  if (editing) return;
  if (event.code === "Space") {
    event.preventDefault();
    state.space = true;
    $("canvas").classList.add("panning");
    return;
  }
  if (event.ctrlKey || event.metaKey) {
    if (event.key.toLowerCase() === "z") {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
    } else if (event.key.toLowerCase() === "s") {
      event.preventDefault();
      flush().catch(showError);
    }
    return;
  }
  const keys = {
    v: "select",
    b: "bird",
    h: "head",
    e: "eye",
    p: "anchor",
    u: "uncertain",
  };
  if (keys[event.key.toLowerCase()]) {
    event.preventDefault();
    setTool(keys[event.key.toLowerCase()]);
  } else if (event.key.toLowerCase() === "f") fit();
  else if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    removeSelected();
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    navigate(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    navigate(1);
  } else if (event.key === "Enter") {
    event.preventDefault();
    submit();
  } else if (event.key === "Escape") {
    state.selected = null;
    setTool("select");
    renderShapes();
    renderProperties();
  }
});
document.addEventListener("keyup", (event) => {
  if (event.code === "Space") {
    state.space = false;
    $("canvas").classList.remove("panning");
  }
});
window.addEventListener("blur", () => {
  state.space = false;
  $("canvas").classList.remove("panning");
});
window.addEventListener("beforeunload", (event) => {
  if (state.dirty || state.saving) {
    persistLocal();
    event.preventDefault();
    event.returnValue = "";
  }
});
new ResizeObserver(() => {
  if (state.a) {
    $("zoomValue").textContent = Math.round(screenScale() * 100) + "%";
    renderShapes();
  }
}).observe($("stage"));
async function boot() {
  try {
    const result = await api("/api/dataset");
    state.rows = result.images;
    translate();
    if (!state.rows.length) {
      $("emptyState").textContent =
        state.lang === "zh"
          ? "工作区尚无素材，请先运行导入命令。"
          : "Workspace empty. Run the import command first.";
      return;
    }
    const last = localStorage.getItem("fba-last-image");
    await loadImage(
      state.rows.some((r) => r.image_id === last)
        ? last
        : state.rows[0].image_id,
    );
    setInterval(refreshDataset, 15000);
  } catch (e) {
    connection("offline");
    $("emptyState").textContent = t("loadError") + ": " + e.message;
  }
}
boot();
