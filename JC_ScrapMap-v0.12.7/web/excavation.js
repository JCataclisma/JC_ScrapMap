"use strict";

const canvas = document.getElementById("excavationCanvas");
const context = canvas.getContext("2d");
const details = document.getElementById("details");
let island = null;
let zoom = 1;
let viewCenter = null;
const minimumZoom = 1;
const maximumZoom = 8;

const terrainColors = {
  lake: "#214b62",
  meadow: "#536947",
  forest: "#28503a",
  desert: "#8b6d3b",
  field: "#788051",
  "burnt-forest": "#65463c",
  "autumn-forest": "#76506d",
  unknown: "#303b34",
};

const pointStyles = {
  asset: ["#81917e", 0.75, 0.34],
  blueprint: ["#e2c878", 1.7, 0.82],
  harvestable: ["#68b66b", 1.15, 0.62],
  kinematic: ["#d98262", 2.1, 0.9],
  prefab: ["#c48cce", 1.9, 0.82],
  ruin: ["#bb83c7", 2.3, 0.92],
  node: ["#8ca4bf", 0.9, 0.38],
  "potato-spawn": ["#8ca4bf", 1.4, 0.7],
  quest: ["#56ccf2", 3.4, 1],
  loot: ["#f1bd54", 3.2, 1],
  "epic-loot": ["#d65aff", 4.4, 1],
  "enemy-spawn": ["#df695f", 1.8, 0.88],
};

function tileKind(name) {
  if (name.includes("Mountain")) return ["#6a6252", "#b2a789"];
  if (name.includes("KinematicBridge")) return ["#a78151", "#e0bb78"];
  return ["#b9a36e", "#ead59b"];
}

function draw() {
  if (!island) return;
  const ratio = devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.fillStyle = "#080b09";
  context.fillRect(0, 0, width, height);

  const bounds = island.bounds;
  const padding = 42;
  const fittedScale = Math.min(
    (width - padding * 2) / Math.max(1, bounds.xMax - bounds.xMin),
    (height - padding * 2) / Math.max(1, bounds.yMax - bounds.yMin),
  );
  const scale = fittedScale * zoom;
  if (!viewCenter) {
    viewCenter = {
      x: (bounds.xMin + bounds.xMax) / 2,
      y: (bounds.yMin + bounds.yMax) / 2,
    };
  }
  const point = (x, y) => [
    width / 2 + (x - viewCenter.x) * scale,
    height / 2 - (y - viewCenter.y) * scale,
  ];
  const cellPixels = island.cellSizeMeters * scale;

  for (const cell of island.terrainCells) {
    const at = point(
      cell.cellX * island.cellSizeMeters,
      (cell.cellY + 1) * island.cellSizeMeters,
    );
    context.fillStyle = terrainColors[cell.terrain] || terrainColors.unknown;
    context.fillRect(at[0], at[1], cellPixels + 0.5, cellPixels + 0.5);
  }

  for (const cell of island.tileCells) {
    const at = point(
      cell.cellX * island.cellSizeMeters,
      (cell.cellY + 1) * island.cellSizeMeters,
    );
    const [fill] = tileKind(cell.tile);
    context.fillStyle = `${fill}99`;
    context.fillRect(at[0], at[1], cellPixels + 0.5, cellPixels + 0.5);
  }

  for (const placement of island.placements) {
    const at = point(
      placement.originCellX * island.cellSizeMeters,
      (placement.originCellY + placement.sizeCells) * island.cellSizeMeters,
    );
    const [, stroke] = tileKind(placement.developerTile);
    context.strokeStyle = stroke;
    context.lineWidth = 1.5;
    context.strokeRect(
      at[0] + 0.5,
      at[1] + 0.5,
      placement.sizeCells * cellPixels - 1,
      placement.sizeCells * cellPixels - 1,
    );
  }

  context.strokeStyle = "#263d32";
  context.lineWidth = 1;
  for (let x = Math.ceil(bounds.xMin / 64) * 64; x <= bounds.xMax; x += 64) {
    const a = point(x, bounds.yMin);
    const b = point(x, bounds.yMax);
    context.beginPath();
    context.moveTo(...a);
    context.lineTo(...b);
    context.stroke();
  }
  for (let y = Math.ceil(bounds.yMin / 64) * 64; y <= bounds.yMax; y += 64) {
    const a = point(bounds.xMin, y);
    const b = point(bounds.xMax, y);
    context.beginPath();
    context.moveTo(...a);
    context.lineTo(...b);
    context.stroke();
  }

  for (const item of island.points) {
    const style = pointStyles[item.kind] || pointStyles[item.category?.replace(/s$/, "")] || pointStyles.node;
    const at = point(item.x, item.y);
    context.globalAlpha = style[2];
    context.fillStyle = style[0];
    context.beginPath();
    context.arc(at[0], at[1], style[1], 0, Math.PI * 2);
    context.fill();
  }
  context.globalAlpha = 1;

  for (const beacon of island.beacons || []) {
    const at = point(beacon.x, beacon.y);
    context.save();
    context.translate(at[0], at[1]);
    context.rotate(Math.PI / 4);
    context.fillStyle = beacon.color || "#e8f2eb";
    context.strokeStyle = "#080b09";
    context.lineWidth = 2;
    context.fillRect(-7, -7, 14, 14);
    context.strokeRect(-7, -7, 14, 14);
    context.restore();
  }

  if (island.elevator) {
    const at = point(island.elevator.x, island.elevator.y);
    context.fillStyle = "#ff573d";
    context.strokeStyle = "#ffd2c9";
    context.lineWidth = 2;
    context.beginPath();
    context.arc(at[0], at[1], 7, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  }

  context.font = "bold 12px Segoe UI";
  context.textAlign = "center";
  context.textBaseline = "bottom";
  for (const label of island.labels) {
    const at = point(label.x, label.y);
    const textWidth = context.measureText(label.title).width;
    context.fillStyle = "rgb(8 13 10 / 78%)";
    context.fillRect(at[0] - textWidth / 2 - 3, at[1] - 18, textWidth + 6, 16);
    context.fillStyle = "#edf4ef";
    context.fillText(label.title, at[0], at[1] - 4);
  }
  for (const beacon of island.beacons || []) {
    const at = point(beacon.x, beacon.y);
    const label = beacon.iconName || "Beacon";
    const textWidth = context.measureText(label).width;
    context.fillStyle = "rgb(8 13 10 / 82%)";
    context.fillRect(at[0] - textWidth / 2 - 3, at[1] - 27, textWidth + 6, 16);
    context.fillStyle = beacon.color || "#e8f2eb";
    context.fillText(label, at[0], at[1] - 13);
  }
  if (island.elevator) {
    const at = point(island.elevator.x, island.elevator.y);
    context.fillStyle = "rgb(8 13 10 / 82%)";
    context.fillRect(at[0] - 65, at[1] + 9, 130, 17);
    context.fillStyle = "#ffd2c9";
    context.fillText("Saved elevator portal", at[0], at[1] + 24);
  }

  context.textAlign = "left";
  context.textBaseline = "alphabetic";
  context.fillStyle = "#b8c7be";
  context.font = "12px Segoe UI";
  context.fillText("+Y north", 12, 20);
  document.getElementById("zoomOut").disabled = zoom <= minimumZoom;
  document.getElementById("zoomIn").disabled = zoom >= maximumZoom;
}

function fittedScale() {
  if (!island) return 1;
  const padding = 42;
  return Math.min(
    (canvas.clientWidth - padding * 2) / Math.max(1, island.bounds.xMax - island.bounds.xMin),
    (canvas.clientHeight - padding * 2) / Math.max(1, island.bounds.yMax - island.bounds.yMin),
  );
}

function changeZoom(nextZoom, anchorX = canvas.clientWidth / 2, anchorY = canvas.clientHeight / 2) {
  if (!island || !viewCenter) return;
  const clamped = Math.max(minimumZoom, Math.min(maximumZoom, nextZoom));
  if (clamped === zoom) return;
  const oldScale = fittedScale() * zoom;
  const worldX = viewCenter.x + (anchorX - canvas.clientWidth / 2) / oldScale;
  const worldY = viewCenter.y - (anchorY - canvas.clientHeight / 2) / oldScale;
  zoom = clamped;
  const newScale = fittedScale() * zoom;
  viewCenter.x = worldX - (anchorX - canvas.clientWidth / 2) / newScale;
  viewCenter.y = worldY + (anchorY - canvas.clientHeight / 2) / newScale;
  if (zoom === minimumZoom) {
    viewCenter.x = (island.bounds.xMin + island.bounds.xMax) / 2;
    viewCenter.y = (island.bounds.yMin + island.bounds.yMax) / 2;
  }
  draw();
}

fetch("../generated/state.json", { cache: "no-store" })
  .then((response) => response.json())
  .then(async (state) => {
    const metadata = state.excavationIsland;
    if (metadata?.status !== "available") {
      throw new Error(metadata?.message || "Excavation Island map is unavailable.");
    }
    const response = await fetch(`../generated/${metadata.dataFile}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Excavation Island map data could not be loaded.");
    island = await response.json();
    const summary = island.summary;
    document.getElementById("subtitle").textContent =
      `Overworld 1 · ${summary.authoredTileCells} authored terrain cells · ${summary.schematicPoints} authored points`;
    document.getElementById("connection").textContent = island.elevator
      ? `Elevator cell ${island.elevator.cellX}, ${island.elevator.cellY} → world ${island.elevator.destinationWorldId}`
      : "Saved elevator portal not yet present";
    details.textContent =
      `${summary.ruinPoints} ruin details · ${summary.lootPoints} loot spawns · `
      + `${summary.epicLootPoints} epic loot spawns · ${summary.enemySpawnPoints} enemy spawns · `
      + `${summary.beaconCount || 0} saved physical beacons. `
      + "The surface layout comes from the installed fixed island world; the elevator cell comes from the selected save.";
    draw();
  })
  .catch((error) => {
    details.textContent = error.message;
    document.getElementById("subtitle").textContent = "Map unavailable";
  });

addEventListener("resize", draw);

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const factor = event.deltaY > 0 ? 1 / 1.25 : 1.25;
  changeZoom(zoom * factor, event.clientX - rect.left, event.clientY - rect.top);
}, { passive: false });

document.getElementById("zoomIn").addEventListener("click", () => {
  changeZoom(zoom * 1.25);
});

document.getElementById("zoomOut").addEventListener("click", () => {
  changeZoom(zoom / 1.25);
});
