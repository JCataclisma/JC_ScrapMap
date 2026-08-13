"use strict";
const canvas = document.getElementById("undergroundCanvas");
const context = canvas.getContext("2d");
const details = document.getElementById("details");
const depth = Number(new URLSearchParams(location.search).get("depth"));
const slider = document.getElementById("elevation");
const elevationValue = document.getElementById("elevationValue");
const showAll = document.getElementById("showAllTunnels");
const showChanges = document.getElementById("showVoxelChanges");
let floor = null;

const tunnelColors = { TtVeinT1: "#45bbed", TtVeinRich: "#f1bd54", TtVeinSparkstone: "#d65aff" };
const pocketColors = { resource: "#347a48", chamber: "#7769a8", passage: "#ffffff", special: "#a35a82" };

function draw() {
  const terrain = floor?.terrain3d;
  if (!terrain) return;
  const ratio = devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.fillStyle = "#090d0b";
  context.fillRect(0, 0, width, height);

  const xs = [], ys = [];
  for (const tunnel of terrain.tunnels) for (const point of tunnel.positions) { xs.push(point.x); ys.push(point.y); }
  for (const cell of terrain.pocketCells) for (const record of cell.records) {
    xs.push((cell.cellX * 4 + record.xChunkWithinCell) * 16, (cell.cellX * 4 + record.xChunkWithinCell + record.sizeXChunks) * 16);
    ys.push((cell.cellY * 4 + record.yChunkWithinCell) * 16, (cell.cellY * 4 + record.yChunkWithinCell + record.sizeYChunks) * 16);
  }
  for (const cell of terrain.caveCells) { xs.push(cell.cellX * 64, (cell.cellX + 1) * 64); ys.push(cell.cellY * 64, (cell.cellY + 1) * 64); }
  for (const cell of floor.cells || []) { xs.push(cell.x * 64, (cell.x + 1) * 64); ys.push(cell.y * 64, (cell.y + 1) * 64); }
  if (!xs.length) return;
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const padding = 34;
  const scale = Math.min((width - padding * 2) / Math.max(1, maxX - minX), (height - padding * 2) / Math.max(1, maxY - minY));
  const left = (width - (maxX - minX) * scale) / 2;
  const top = (height - (maxY - minY) * scale) / 2;
  const point = (x, y) => [left + (x - minX) * scale, top + (maxY - y) * scale];
  const z = Number(slider.value);

  context.strokeStyle = "#1f3128"; context.lineWidth = 1;
  for (let x = Math.ceil(minX / 64) * 64; x <= maxX; x += 64) { const a = point(x, minY), b = point(x, maxY); context.beginPath(); context.moveTo(...a); context.lineTo(...b); context.stroke(); }
  for (let y = Math.ceil(minY / 64) * 64; y <= maxY; y += 64) { const a = point(minX, y), b = point(maxX, y); context.beginPath(); context.moveTo(...a); context.lineTo(...b); context.stroke(); }

  for (const cell of terrain.caveCells) for (const record of cell.records) if (z >= record.zChunk * 16 && z < (record.zChunk + record.heightChunks) * 16) {
    const a = point(cell.cellX * 64, (cell.cellY + 1) * 64);
    context.fillStyle = terrain.tunnelCount || terrain.pocketRecordCount ? "#52615a55" : "#63786dcc";
    context.fillRect(a[0], a[1], 64 * scale, 64 * scale);
    if (!terrain.tunnelCount && !terrain.pocketRecordCount) { context.strokeStyle = "#a7c4b5"; context.lineWidth = 1; context.strokeRect(a[0] + 0.5, a[1] + 0.5, 64 * scale - 1, 64 * scale - 1); }
  }
  if (!terrain.caveRecordCount && !terrain.pocketRecordCount && !terrain.tunnelCount) for (const cell of floor.cells || []) {
    const a = point(cell.x * 64, (cell.y + 1) * 64); context.fillStyle = cell.authored ? "#52615a" : "#26312b"; context.fillRect(a[0], a[1], 64 * scale - 1, 64 * scale - 1);
  }
  for (const cell of terrain.pocketCells) for (const record of cell.records) if (z >= record.zChunk * 16 && z < (record.zChunk + record.sizeZChunks) * 16) {
    const a = point((cell.cellX * 4 + record.xChunkWithinCell) * 16, (cell.cellY * 4 + record.yChunkWithinCell + record.sizeYChunks) * 16);
    context.globalAlpha = record.category === "passage" ? 0.72 : 0.5;
    context.fillStyle = pocketColors[record.category] || "#888";
    context.fillRect(a[0], a[1], record.sizeXChunks * 16 * scale, record.sizeYChunks * 16 * scale);
  }
  context.globalAlpha = 1;
  for (const tunnel of terrain.tunnels) {
    context.strokeStyle = tunnelColors[tunnel.type] || "#aaa"; context.lineWidth = Math.max(1.5, 5 * scale); context.globalAlpha = showAll.checked ? 0.18 : 1;
    let active = false; context.beginPath();
    for (const p of tunnel.positions) { const near = Math.abs(p.z - z) <= 8; if (near || showAll.checked) { const a = point(p.x, p.y); if (active) context.lineTo(...a); else context.moveTo(...a); active = true; } else active = false; }
    context.stroke();
  }
  context.globalAlpha = 1;
  if (showChanges.checked) { context.save(); context.strokeStyle = "#f5f5f5"; context.lineWidth = 1.5; context.setLineDash([6, 5]); for (const cell of terrain.savedVoxelChangeCells) { const a = point(cell.cellX * 64, (cell.cellY + 1) * 64); context.strokeRect(a[0] + 2, a[1] + 2, 64 * scale - 4, 64 * scale - 4); } context.restore(); }
  for (const elevator of terrain.elevatorMarkers) if (Math.abs(elevator.z - z) <= 8) {
    const a = point(elevator.x, elevator.y), length = 24, norm = Math.hypot(elevator.facingX, elevator.facingY) || 1;
    context.strokeStyle = context.fillStyle = "#ff573d"; context.lineWidth = 4; context.beginPath(); context.arc(a[0], a[1], 8, 0, Math.PI * 2); context.fill(); context.beginPath(); context.moveTo(...a); context.lineTo(a[0] + elevator.facingX / norm * length, a[1] - elevator.facingY / norm * length); context.stroke();
    context.font = "bold 13px system-ui"; const label = `Elevator ${elevator.z.toFixed(0)} m`, textWidth = context.measureText(label).width; context.fillText(label, Math.max(6, Math.min(width - textWidth - 6, a[0] + 12)), Math.max(16, Math.min(height - 6, a[1] - 12)));
  }
  if (floor.floorKind === "authored-mine") for (const resource of terrain.authoredResourcePoints || []) if (Math.abs(resource.z - z) <= 8) {
    const a = point(resource.x, resource.y);
    context.fillStyle = resource.material === "Quartz" ? "#d8f4ff" : "#72d36b";
    context.strokeStyle = resource.material === "Quartz" ? "#65cce9" : "#b6ffad";
    context.lineWidth = 1.5; context.beginPath(); context.arc(a[0], a[1], resource.material === "Quartz" ? 6 : 3, 0, Math.PI * 2); context.fill(); context.stroke();
  }
  elevationValue.textContent = `${z} m`;
}

fetch("../generated/state.json", { cache: "no-store" }).then(response => response.json()).then(async state => {
  floor = state.underground?.floors?.find(item => item.depth === depth && item.generated);
  if (!floor) throw new Error("This floor is not generated in the selected save.");
  let terrain = floor.terrain3d;
  if (!terrain) throw new Error("No decoded 3D terrain is available for this floor.");
  if (terrain.dataFile) {
    const response = await fetch(`../generated/${terrain.dataFile}`, { cache: "no-store" });
    if (!response.ok) throw new Error("The decoded underground terrain file could not be loaded.");
    terrain = await response.json();
    floor.terrain3d = terrain;
  }
  document.title = `JC ScrapMap · ${floor.name}`;
  document.getElementById("title").textContent = `Level ${floor.depth}: ${floor.name}`;
  document.getElementById("subtitle").textContent = `Saved world ${floor.worldId} · ${terrain.caveRecordCount} caves · ${terrain.pocketRecordCount} pockets · ${terrain.tunnelCount} tunnels`;
  document.getElementById("vault").textContent = `Vault ${new Intl.NumberFormat("en-US").format(state.underground.vaultTotal)}`;
  const elevator = terrain.elevatorMarkers[0];
  const kindText = floor.floorKind === "procedural-mine" ? "Procedural mine" : floor.floorKind === "authored-mine" ? "Authored mine" : floor.floorKind === "boss" ? "Boss/combat area" : "Fixed facility/passage area";
  const resources = terrain.authoredResourcePoints || [];
  const quartzCount = resources.filter(item => item.material === "Quartz").length;
  const goopiteCount = resources.filter(item => item.material === "Goopite").length;
  const resourceText = floor.floorKind === "authored-mine" ? ` Original authored evidence: ${quartzCount} Quartz placements and ${goopiteCount} Goopite feature centers; mined/depleted state is not decoded.` : "";
  details.textContent = `${kindText}. ` + (elevator ? `Elevator connection: X ${elevator.x.toFixed(1)} m, Y ${elevator.y.toFixed(1)} m, Z ${elevator.z.toFixed(1)} m. Arrow: authored facing direction.` : "No elevator connection was resolved for this floor.") + resourceText;
  document.getElementById("pocketLegend").hidden = !terrain.pocketRecordCount;
  document.getElementById("tunnelLegend").hidden = !terrain.tunnelCount;
  document.getElementById("authoredResourceLegend").hidden = floor.floorKind !== "authored-mine";
  const ranges = [terrain.tunnelZRangeMeters, terrain.caveZChunkRange?.map(value => value * 16), terrain.pocketZChunkRange?.map(value => value * 16)].filter(Boolean).flat();
  slider.min = Math.floor(Math.min(0, ...ranges) / 4) * 4; slider.max = Math.ceil(Math.max(16, ...ranges) / 4) * 4; slider.value = elevator ? Math.round(elevator.z / 4) * 4 : slider.min;
  if (floor.floorKind === "authored-mine" && resources.length) {
    const candidates = [...new Set(resources.map(item => Math.round(item.z / 4) * 4))];
    slider.value = candidates.reduce((best, candidate) => {
      const visible = resources.filter(item => Math.abs(item.z - candidate) <= 8).length;
      const bestVisible = resources.filter(item => Math.abs(item.z - best) <= 8).length;
      return visible > bestVisible ? candidate : best;
    }, candidates[0]);
  }
  draw();
}).catch(error => { details.textContent = error.message; });
slider.oninput = draw; showAll.onchange = draw; showChanges.onchange = draw; addEventListener("resize", draw);
