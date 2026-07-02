const TYPE_LABEL = {
  attack: "进攻",
  free_kick: "任意球",
  corner: "角球",
  throw_in: "界外球",
  penalty: "点球",
  goalkeep: "守门",
};

const DUTY_LABEL = {
  1: "GK",
  2: "DF",
  3: "FW",
};

const state = {
  protocol: null,
  defaultAngle: 120,
  presets: [],
  selectedId: null,
  typeFilter: "all",
  query: "",
  edits: new Map(),
  selection: { kind: "none" },
  drag: null,
  layout: null,
  showMax: true,
  showMin: true,
};

const els = {
  status: document.querySelector("#statusText"),
  reload: document.querySelector("#reloadButton"),
  save: document.querySelector("#saveButton"),
  filters: document.querySelector("#typeFilters"),
  search: document.querySelector("#searchInput"),
  list: document.querySelector("#presetList"),
  canvas: document.querySelector("#fieldCanvas"),
  title: document.querySelector("#presetTitle"),
  meta: document.querySelector("#presetMeta"),
  showMax: document.querySelector("#showMaxAngle"),
  showMin: document.querySelector("#showMinAngle"),
  selectionInfo: document.querySelector("#selectionInfo"),
  addHomePlayer: document.querySelector("#addHomePlayerButton"),
  addAwayPlayer: document.querySelector("#addAwayPlayerButton"),
  deletePlayer: document.querySelector("#deletePlayerButton"),
  angleMax: document.querySelector("#angleMaxInput"),
  angleMin: document.querySelector("#angleMinInput"),
  centerShift: document.querySelector("#centerShiftInput"),
  margin: document.querySelector("#marginInput"),
  angleCheck: document.querySelector("#angleCheck"),
  patchPreview: document.querySelector("#patchPreview"),
};

const ctx = els.canvas.getContext("2d");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function round(value, digits = 2) {
  const mul = 10 ** digits;
  return Math.round(Number(value) * mul) / mul;
}

function normalizeVec(vec) {
  const x = Number(vec.x) || 0;
  const z = Number(vec.z) || 0;
  const len = Math.hypot(x, z) || 1;
  return { x: round(x / len, 3), y: 0, z: round(z / len, 3) };
}

function yawDeg(vec) {
  return round((Math.atan2(vec.x, vec.z) * 180) / Math.PI, 1);
}

function faceToward(from, to) {
  return yawDeg({ x: to.x - from.x, z: to.z - from.z });
}

function distanceToGoalCenter(pos) {
  return Math.hypot(Number(pos.x) || 0, Number(pos.z) || 0);
}

function formatMeters(value) {
  return `${round(value, 1)}m`;
}

function hydratePreset(row) {
  const preset = {
    ID: Number(row.ID),
    SliceType: row.SliceType,
    NameLcKey: row.NameLcKey,
    Tags: row.TagsParsed || [],
    BallPos: clone(row.BallPosParsed),
    BallVector: normalizeVec(row.BallVectorParsed),
    BallOwner: Number(row.BallOwner),
    PlayersInit: clone(row.PlayersInitParsed),
    TargetPoint: row.TargetPointParsed ? clone(row.TargetPointParsed) : null,
    DisplayAngle: Number(row.DisplayAngle) || state.defaultAngle,
    Remark: row.Remark || "",
  };
  preset._base = makePatch(preset);
  return preset;
}

function makePatch(preset) {
  return {
    ID: preset.ID,
    BallPos: {
      x: round(preset.BallPos.x, 3),
      y: round(preset.BallPos.y || 0, 3),
      z: round(preset.BallPos.z, 3),
    },
    BallVector: normalizeVec(preset.BallVector),
    BallOwner: Number(preset.BallOwner),
    PlayersInit: preset.PlayersInit.map((player) => ({
      team: player.team,
      idx: Number(player.idx),
      duty: Number(player.duty),
      pos: {
        x: round(player.pos.x, 3),
        y: round(player.pos.y || 0, 3),
        z: round(player.pos.z, 3),
      },
      facing: round(player.facing || 0, 1),
    })),
    TargetPoint: preset.TargetPoint
      ? { x: round(preset.TargetPoint.x, 3), y: round(preset.TargetPoint.y || 0, 3), z: round(preset.TargetPoint.z, 3) }
      : null,
  };
}

function patchKey(patch) {
  return JSON.stringify(patch);
}

function currentPreset() {
  return state.presets.find((preset) => preset.ID === state.selectedId) || state.presets[0] || null;
}

function markDirty(preset) {
  const patch = makePatch(preset);
  if (patchKey(patch) === patchKey(preset._base)) {
    state.edits.delete(preset.ID);
  } else {
    state.edits.set(preset.ID, patch);
  }
  renderList();
  updateInspector();
}

function resizeCanvas() {
  const rect = els.canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(480, Math.round(rect.width * dpr));
  const height = Math.max(760, Math.round(rect.height * dpr));
  if (els.canvas.width !== width || els.canvas.height !== height) {
    els.canvas.width = width;
    els.canvas.height = height;
  }
  renderCanvas();
}

function computeLayout() {
  const pad = 42;
  const width = els.canvas.width;
  const height = els.canvas.height;
  const scale = Math.min((width - pad * 2) / 36, (height - pad * 2) / 60);
  const fieldW = 36 * scale;
  const fieldH = 60 * scale;
  return {
    scale,
    x: (width - fieldW) / 2,
    y: (height - fieldH) / 2,
    w: fieldW,
    h: fieldH,
  };
}

function toScreen(pos) {
  const layout = state.layout;
  return {
    x: layout.x + (Number(pos.x) + 18) * layout.scale,
    y: layout.y + (0 - Number(pos.z)) * layout.scale,
  };
}

function toWorld(point) {
  const layout = state.layout;
  return {
    x: round((point.x - layout.x) / layout.scale - 18, 2),
    y: 0,
    z: round(0 - (point.y - layout.y) / layout.scale, 2),
  };
}

function clampWorld(pos) {
  const p = state.protocol;
  return {
    x: Math.max(-p.field_x_half, Math.min(p.field_x_half, pos.x)),
    y: 0,
    z: Math.max(p.field_z_far, Math.min(p.field_z_near, pos.z)),
  };
}

function teamPlayers(preset, team) {
  return preset.PlayersInit
    .filter((player) => player.team === team)
    .sort((a, b) => Number(a.idx) - Number(b.idx));
}

function renumberPlayers(preset) {
  const orderedPlayers = [];
  for (const team of ["home", "away"]) {
    const players = teamPlayers(preset, team);
    players.forEach((player, idx) => {
      player.idx = idx;
      orderedPlayers.push(player);
    });
  }
  preset.PlayersInit = orderedPlayers;
}

function nearestHomePlayerToBall(preset) {
  return teamPlayers(preset, "home")
    .map((player) => ({
      player,
      distance: Math.hypot(player.pos.x - preset.BallPos.x, player.pos.z - preset.BallPos.z),
    }))
    .sort((a, b) => a.distance - b.distance)[0]?.player || null;
}

function playerDropPosition(preset, team) {
  const count = teamPlayers(preset, team).length;
  const vec = normalizeVec(preset.BallVector);
  const side = count % 2 === 0 ? 1 : -1;
  const lane = Math.ceil(count / 2) * 1.8 * side;
  const depth = team === "home" ? 3.2 + Math.floor(count / 3) * 1.4 : 4.2 + Math.floor(count / 3) * 1.2;
  const right = { x: vec.z, z: -vec.x };
  return clampWorld({
    x: preset.BallPos.x + vec.x * depth + right.x * lane,
    y: 0,
    z: preset.BallPos.z + vec.z * depth + right.z * lane,
  });
}

function addPlayer(team) {
  const preset = currentPreset();
  if (!preset) return;
  const pos = playerDropPosition(preset, team);
  const player = {
    team,
    idx: teamPlayers(preset, team).length,
    duty: team === "home" ? 3 : 2,
    pos,
    facing: team === "home" ? faceToward(pos, { x: 0, z: 0 }) : faceToward(pos, preset.BallPos),
  };
  preset.PlayersInit.push(player);
  renumberPlayers(preset);
  state.selection = { kind: "player", team, idx: teamPlayers(preset, team).length - 1 };
  markDirty(preset);
  renderAll();
}

function deleteSelectedPlayer() {
  const preset = currentPreset();
  const selected = state.selection;
  if (!preset || selected.kind !== "player") return;
  if (selected.team === "home" && teamPlayers(preset, "home").length <= 1) {
    els.status.textContent = "至少需要保留一名我方球员";
    return;
  }

  const ownerBeforeDelete = teamPlayers(preset, "home").find((player) => Number(player.idx) === Number(preset.BallOwner));
  const deletesOwner = selected.team === "home" && Number(selected.idx) === Number(preset.BallOwner);
  preset.PlayersInit = preset.PlayersInit.filter((player) => (
    player.team !== selected.team || Number(player.idx) !== Number(selected.idx)
  ));
  renumberPlayers(preset);

  if (deletesOwner || !ownerBeforeDelete || !preset.PlayersInit.includes(ownerBeforeDelete)) {
    const nextOwner = nearestHomePlayerToBall(preset);
    if (nextOwner) preset.BallOwner = Number(nextOwner.idx);
  } else {
    preset.BallOwner = Number(ownerBeforeDelete.idx);
  }

  state.selection = { kind: "none" };
  markDirty(preset);
  renderAll();
}

function mousePoint(event) {
  const rect = els.canvas.getBoundingClientRect();
  const sx = els.canvas.width / rect.width;
  const sy = els.canvas.height / rect.height;
  return {
    x: (event.clientX - rect.left) * sx,
    y: (event.clientY - rect.top) * sy,
  };
}

function drawField() {
  const l = state.layout;
  ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
  ctx.fillStyle = "#2d5b84";
  ctx.fillRect(0, 0, els.canvas.width, els.canvas.height);

  for (let i = 0; i < 12; i += 1) {
    ctx.fillStyle = i % 2 === 0 ? "#188349" : "#137642";
    ctx.fillRect(l.x, l.y + (l.h / 12) * i, l.w, l.h / 12);
  }

  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 2;
  ctx.strokeRect(l.x, l.y, l.w, l.h);

  const centerY = toScreen({ x: 0, z: -30 }).y;
  ctx.beginPath();
  ctx.moveTo(l.x, centerY);
  ctx.lineTo(l.x + l.w, centerY);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(toScreen({ x: 0, z: -30 }).x, centerY, 4.5 * l.scale, 0, Math.PI * 2);
  ctx.stroke();

  drawBox(-11.5, -10, 23, 10);
  drawBox(-3.2, -3.5, 6.4, 3.5);
  drawBox(-4.25, -0.7, 8.5, 0.7, "rgba(255,255,255,0.7)");

  ctx.fillStyle = "rgba(16,26,38,0.65)";
  const goal = toScreen({ x: 0, z: 0 });
  ctx.fillRect(goal.x - 4.25 * l.scale, goal.y - 10, 8.5 * l.scale, 10);
}

function drawBox(x, z, w, h, color = "rgba(255,255,255,0.9)") {
  const topLeft = toScreen({ x, z: 0 });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.strokeRect(topLeft.x, topLeft.y, w * state.layout.scale, h * state.layout.scale);
}

function drawWedge(preset, span, fillColor, strokeColor = "rgba(255, 211, 79, 0.95)") {
  if (!span || span <= 0) return;
  const ball = toScreen(preset.BallPos);
  const vec = normalizeVec(preset.BallVector);
  const radius = Math.min(18, Math.max(10, Math.abs(preset.BallPos.z) * 0.7)) * state.layout.scale;
  const center = Math.atan2(-vec.z, vec.x);
  const half = (span / 2) * (Math.PI / 180);
  const start = center - half;
  const end = center + half;

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(ball.x, ball.y);
  ctx.arc(ball.x, ball.y, radius, start, end, false);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(ball.x, ball.y, radius, start, end, false);
  ctx.stroke();

  for (const angle of [start, end]) {
    ctx.beginPath();
    ctx.moveTo(ball.x, ball.y);
    ctx.lineTo(ball.x + Math.cos(angle) * radius, ball.y + Math.sin(angle) * radius);
    ctx.stroke();
  }
  ctx.restore();
}

function drawVectorHandle(preset) {
  const ball = toScreen(preset.BallPos);
  const vec = normalizeVec(preset.BallVector);
  const radius = 10 * state.layout.scale;
  const handle = {
    x: ball.x + vec.x * radius,
    y: ball.y - vec.z * radius,
  };
  ctx.strokeStyle = "#ffd34f";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(ball.x, ball.y);
  ctx.lineTo(handle.x, handle.y);
  ctx.stroke();
  ctx.fillStyle = "#ffd34f";
  ctx.beginPath();
  ctx.arc(handle.x, handle.y, 8, 0, Math.PI * 2);
  ctx.fill();
}

function drawPlayers(preset) {
  const selected = state.selection;
  for (const player of preset.PlayersInit) {
    const pos = toScreen(player.pos);
    const isOwner = player.team === "home" && Number(player.idx) === Number(preset.BallOwner);
    const isSelected = selected.kind === "player" && selected.team === player.team && selected.idx === Number(player.idx);
    const color = Number(player.duty) === 1 ? "#f2bb2f" : player.team === "home" ? "#16b978" : "#d94d43";

    ctx.fillStyle = color;
    ctx.strokeStyle = isSelected ? "#111827" : isOwner ? "#fef3c7" : "rgba(255,255,255,0.9)";
    ctx.lineWidth = isSelected ? 4 : isOwner ? 4 : 2;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, isOwner ? 13 : 11, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    const yaw = (Number(player.facing) * Math.PI) / 180;
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.lineTo(pos.x + Math.sin(yaw) * 16, pos.y - Math.cos(yaw) * 16);
    ctx.stroke();

    ctx.fillStyle = "#fff";
    ctx.font = "bold 10px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(`${player.team === "home" ? "H" : "A"}${player.idx}`, pos.x, pos.y);
  }
}

function drawBall(preset) {
  const pos = toScreen(preset.BallPos);
  ctx.fillStyle = "#ff8a1f";
  ctx.strokeStyle = state.selection.kind === "ball" ? "#111827" : "#fff";
  ctx.lineWidth = state.selection.kind === "ball" ? 4 : 2;
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function renderCanvas() {
  const preset = currentPreset();
  if (!preset || !state.protocol) return;
  state.layout = computeLayout();
  drawField();
  if (state.showMax) drawWedge(preset, preset.DisplayAngle || state.defaultAngle, "rgba(255, 211, 79, 0.34)");
  if (state.showMin) drawWedge(preset, preset.DisplayAngle || state.defaultAngle, "rgba(255, 138, 31, 0.18)", "rgba(255, 138, 31, 0.9)");
  drawVectorHandle(preset);
  drawPlayers(preset);
  drawBall(preset);
}

function renderFilters(order) {
  const items = ["all", ...order];
  els.filters.innerHTML = "";
  for (const type of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = type === "all" ? "全部" : TYPE_LABEL[type] || type;
    button.className = state.typeFilter === type ? "active" : "";
    button.addEventListener("click", () => {
      state.typeFilter = type;
      renderFilters(order);
      renderList();
    });
    els.filters.appendChild(button);
  }
}

function filteredPresets() {
  const query = state.query.trim().toLowerCase();
  return state.presets.filter((preset) => {
    if (state.typeFilter !== "all" && preset.SliceType !== state.typeFilter) return false;
    if (!query) return true;
    const haystack = `${preset.ID} ${preset.SliceType} ${preset.Tags.join(" ")} ${preset.Remark}`.toLowerCase();
    return haystack.includes(query);
  });
}

function renderList() {
  const rows = filteredPresets();
  els.list.innerHTML = "";
  for (const preset of rows) {
    const row = document.createElement("div");
    row.className = [
      "preset-row",
      preset.ID === state.selectedId ? "active" : "",
      state.edits.has(preset.ID) ? "dirty" : "",
    ].filter(Boolean).join(" ");
    row.innerHTML = `<strong>${preset.ID} ${TYPE_LABEL[preset.SliceType] || preset.SliceType}</strong><span>${preset.Tags.join(" / ") || preset.NameLcKey}</span>`;
    row.addEventListener("click", () => {
      state.selectedId = preset.ID;
      state.selection = { kind: "none" };
      renderAll();
    });
    els.list.appendChild(row);
  }
}

function angleBetween(a, b) {
  const al = Math.hypot(a.x, a.z);
  const bl = Math.hypot(b.x, b.z);
  if (!al || !bl) return 0;
  const dot = Math.max(-1, Math.min(1, (a.x * b.x + a.z * b.z) / (al * bl)));
  return (Math.acos(dot) * 180) / Math.PI;
}

function angleCheck(preset) {
  if (!["attack", "free_kick", "corner", "throw_in"].includes(preset.SliceType)) {
    return { ok: true, text: "该类型不需要接应夹角检测" };
  }
  const receivers = preset.PlayersInit.filter((player) => player.team === "home" && Number(player.idx) !== Number(preset.BallOwner));
  if (!receivers.length) return { ok: false, text: "没有非控球队友" };
  const limit = preset.DisplayAngle / 2;
  const angles = receivers.map((player) => angleBetween(preset.BallVector, {
    x: player.pos.x - preset.BallPos.x,
    z: player.pos.z - preset.BallPos.z,
  }));
  const best = Math.min(...angles);
  return {
    ok: best <= limit,
    text: `最近接应 ${round(best, 1)}° / 允许 ${round(limit, 1)}°`,
  };
}

function updateInspector() {
  const preset = currentPreset();
  if (!preset) return;
  const goalDistance = distanceToGoalCenter(preset.BallPos);
  els.title.textContent = `${preset.ID} ${TYPE_LABEL[preset.SliceType] || preset.SliceType}`;
  els.meta.textContent = `控球 H${preset.BallOwner}  球向 ${yawDeg(preset.BallVector)}°`;
  els.meta.textContent += `  球距门心 ${formatMeters(goalDistance)}`;

  els.angleMax.value = preset.DisplayAngle;
  els.angleMin.value = preset.DisplayAngle;
  els.centerShift.value = 0;
  els.margin.value = 0;

  const selected = state.selection;
  const info = [];
  info.push(["球距门心", formatMeters(goalDistance)]);
  const owner = hasOwnerSnap(preset);
  if (owner) {
    const d = Math.hypot(preset.BallPos.x - owner.pos.x, preset.BallPos.z - owner.pos.z);
    const expected = Number(state.protocol?.ball_control_distance) || 0.5;
    const drift = Math.abs(d - expected);
    info.push(["球距持球者", `${formatMeters(d)} / 应 ${formatMeters(expected)}${drift < 0.01 ? "" : " ⚠"}`]);
  }
  els.deletePlayer.disabled = selected.kind !== "player";
  if (selected.kind === "player") {
    const player = preset.PlayersInit.find((p) => p.team === selected.team && Number(p.idx) === selected.idx);
    if (player) {
      info.push(["对象", `${player.team === "home" ? "我方" : "对方"} ${DUTY_LABEL[player.duty] || player.duty}${player.idx}`]);
      info.push(["x/z", `${round(player.pos.x, 2)} / ${round(player.pos.z, 2)}`]);
      info.push(["朝向", `${round(player.facing, 1)}°`]);
    }
  } else if (selected.kind === "ball") {
    info.push(["对象", "足球"]);
    info.push(["x/z", `${round(preset.BallPos.x, 2)} / ${round(preset.BallPos.z, 2)}`]);
  } else if (selected.kind === "vector") {
    info.push(["对象", "球向"]);
    info.push(["向量", `${round(preset.BallVector.x, 3)} / ${round(preset.BallVector.z, 3)}`]);
    info.push(["角度", `${yawDeg(preset.BallVector)}°`]);
  } else {
    info.push(["对象", "未选择"]);
  }
  els.selectionInfo.innerHTML = info.map(([k, v]) => `<div><span>${k}</span><strong>${v}</strong></div>`).join("");

  const check = angleCheck(preset);
  els.angleCheck.className = `check ${check.ok ? "ok" : "warn"}`;
  els.angleCheck.textContent = check.text;
  els.patchPreview.value = JSON.stringify({ edits: [...state.edits.values()] }, null, 2);
  els.status.textContent = `${state.presets.length} 个 preset，${state.edits.size} 个未保存改动`;
}

function renderAll() {
  renderList();
  updateInspector();
  renderCanvas();
}

function hitTest(point) {
  const preset = currentPreset();
  if (!preset) return { kind: "none" };
  const hitCandidates = [];
  const ball = toScreen(preset.BallPos);
  const ballDistance = Math.hypot(point.x - ball.x, point.y - ball.y);
  if (ballDistance <= 14) hitCandidates.push({ score: ballDistance / 14, hit: { kind: "ball" } });

  const vec = normalizeVec(preset.BallVector);
  const handle = { x: ball.x + vec.x * 10 * state.layout.scale, y: ball.y - vec.z * 10 * state.layout.scale };
  const handleDistance = Math.hypot(point.x - handle.x, point.y - handle.y);
  if (handleDistance <= 18) hitCandidates.push({ score: handleDistance / 18, hit: { kind: "vector" } });

  for (let i = preset.PlayersInit.length - 1; i >= 0; i -= 1) {
    const player = preset.PlayersInit[i];
    const pos = toScreen(player.pos);
    const radius = 16;
    const distance = Math.hypot(point.x - pos.x, point.y - pos.y);
    if (distance <= radius) {
      hitCandidates.push({ score: distance / radius, hit: { kind: "player", team: player.team, idx: Number(player.idx) } });
    }
  }
  hitCandidates.sort((a, b) => a.score - b.score);
  return hitCandidates[0]?.hit || { kind: "none" };
}

function hasOwnerSnap(preset) {
  if (preset.SliceType === "goalkeep" || preset.SliceType === "penalty" || preset.SliceType === "corner") {
    return null;
  }
  const owner = teamPlayers(preset, "home").find((p) => Number(p.idx) === Number(preset.BallOwner));
  return owner || null;
}

function snapBallToOwner(preset, owner) {
  const distance = Number(state.protocol?.ball_control_distance) || 0.5;
  const yaw = (Number(owner.facing) * Math.PI) / 180;
  const forwardX = Math.sin(yaw);
  const forwardZ = Math.cos(yaw);
  preset.BallPos.x = round(owner.pos.x + forwardX * distance, 3);
  preset.BallPos.z = round(owner.pos.z + forwardZ * distance, 3);
}

function snapOwnerToBall(preset, owner) {
  const distance = Number(state.protocol?.ball_control_distance) || 0.5;
  owner.facing = faceToward(owner.pos, preset.BallPos);
  const yaw = (Number(owner.facing) * Math.PI) / 180;
  const forwardX = Math.sin(yaw);
  const forwardZ = Math.cos(yaw);
  owner.pos.x = round(preset.BallPos.x - forwardX * distance, 3);
  owner.pos.z = round(preset.BallPos.z - forwardZ * distance, 3);
}

function onPointerDown(event) {
  const point = mousePoint(event);
  state.selection = hitTest(point);
  state.drag = state.selection.kind === "none" ? null : { ...state.selection };
  els.canvas.classList.toggle("dragging", Boolean(state.drag));
  renderAll();
}

const OPPONENT_GOAL = { x: 0, z: 0 };

function facingTargetFor(preset, player) {
  if (player.team === "home" && Number(player.idx) !== Number(preset.BallOwner)) {
    return OPPONENT_GOAL;
  }
  return preset.BallPos;
}

function onPointerMove(event) {
  if (!state.drag) return;
  const preset = currentPreset();
  const world = clampWorld(toWorld(mousePoint(event)));
  const owner = hasOwnerSnap(preset);
  if (state.drag.kind === "ball") {
    preset.BallPos.x = world.x;
    preset.BallPos.z = world.z;
    if (owner) snapOwnerToBall(preset, owner);
    for (const p of preset.PlayersInit) {
      if (p.team === "home" && Number(p.idx) === Number(preset.BallOwner)) continue;
      p.facing = faceToward(p.pos, facingTargetFor(preset, p));
    }
  }
  if (state.drag.kind === "vector") {
    preset.BallVector = normalizeVec({ x: world.x - preset.BallPos.x, z: world.z - preset.BallPos.z });
  }
  if (state.drag.kind === "player") {
    const player = preset.PlayersInit.find((p) => p.team === state.drag.team && Number(p.idx) === state.drag.idx);
    if (player) {
      player.pos.x = world.x;
      player.pos.z = world.z;
      if (player.team === "home" && Number(player.idx) === Number(preset.BallOwner)) {
        player.facing = faceToward(player.pos, preset.BallPos);
        snapBallToOwner(preset, player);
      } else {
        player.facing = faceToward(player.pos, facingTargetFor(preset, player));
      }
    }
  }
  markDirty(preset);
  renderCanvas();
}

function onPointerUp() {
  state.drag = null;
  els.canvas.classList.remove("dragging");
}

function bindInputs() {
  const angleInputs = [
    els.angleMax,
    els.angleMin,
  ];
  els.centerShift.disabled = true;
  els.margin.disabled = true;
  for (const input of angleInputs) {
    input.addEventListener("change", () => {
      const preset = currentPreset();
      preset.DisplayAngle = Number(input.value) || state.defaultAngle;
      updateInspector();
      renderCanvas();
    });
  }
  els.addHomePlayer.addEventListener("click", () => addPlayer("home"));
  els.addAwayPlayer.addEventListener("click", () => addPlayer("away"));
  els.deletePlayer.addEventListener("click", deleteSelectedPlayer);
  els.search.addEventListener("input", () => {
    state.query = els.search.value;
    renderList();
  });
  els.showMax.addEventListener("change", () => {
    state.showMax = els.showMax.checked;
    renderCanvas();
  });
  els.showMin.addEventListener("change", () => {
    state.showMin = els.showMin.checked;
    renderCanvas();
  });
  els.reload.addEventListener("click", loadData);
  els.save.addEventListener("click", savePatch);
  els.canvas.addEventListener("pointerdown", onPointerDown);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  window.addEventListener("resize", resizeCanvas);
}

async function loadData() {
  els.status.textContent = "加载 preset";
  const response = await fetch("/api/presets");
  if (!response.ok) throw new Error(await response.text());
  const payload = await response.json();
  state.protocol = payload.coordinate_protocol;
  state.defaultAngle = Number(payload.default_angle) || 120;
  state.presets = payload.presets.map(hydratePreset);
  state.selectedId = state.presets[0]?.ID || null;
  state.edits.clear();
  renderFilters(payload.slice_type_order || []);
  resizeCanvas();
  renderAll();
}

async function savePatch() {
  const edits = [...state.edits.values()];
  const response = await fetch("/api/save-edits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edits }),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    els.status.textContent = `保存失败：${result.error || response.statusText}`;
    return;
  }
  els.status.textContent = `已保存 ${result.saved} 条补丁：${result.path}`;
}

bindInputs();
loadData().catch((error) => {
  els.status.textContent = `加载失败：${error.message}`;
});
