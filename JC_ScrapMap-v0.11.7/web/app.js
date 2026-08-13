"use strict";

const overlayMode = new URLSearchParams(window.location.search).get("overlay") === "1";
if (overlayMode) {
  document.title = "JC ScrapMap Overlay";
  document.body.classList.add("overlay-mode");
}

const canvas = document.getElementById("mapCanvas");
const context = canvas.getContext("2d");
const presets = [100, 250, 500, 1000, 2000, 3000, 5000, 10000];

let state = null;
let viewWidthMeters = 1000;
let center = { x: 0, y: 0 };
let dragging = false;
let dragStart = null;
let switchingSave = false;
let selectedFeature = null;
let selectedVehicle = null;
let editingMarker = null;
let markerPosition = null;
const layerVisibility = new Map();
const appLayout = document.getElementById("appLayout");
const PANEL_LAYOUT_KEY = "jc-scrapmap-panel-widths-v1";
const DEFAULT_PANEL_WIDTHS = { left: 250, right: 270 };
const MIN_MAP_WIDTH = 300;

function loadPanelWidths() {
  try {
    const saved = JSON.parse(localStorage.getItem(PANEL_LAYOUT_KEY));
    return {
      left: Number.isFinite(saved?.left) ? Math.max(0, saved.left) : DEFAULT_PANEL_WIDTHS.left,
      right: Number.isFinite(saved?.right) ? Math.max(0, saved.right) : DEFAULT_PANEL_WIDTHS.right,
    };
  } catch {
    return { ...DEFAULT_PANEL_WIDTHS };
  }
}

let panelWidths = loadPanelWidths();

function applyPanelWidths() {
  appLayout.style.setProperty("--left-panel-width", `${panelWidths.left}px`);
  appLayout.style.setProperty("--right-panel-width", `${panelWidths.right}px`);
}

function savePanelWidths() {
  localStorage.setItem(PANEL_LAYOUT_KEY, JSON.stringify(panelWidths));
}

function availablePanelSpace() {
  const splitterCount = window.matchMedia("(max-width: 900px)").matches ? 1 : 2;
  return Math.max(0, appLayout.clientWidth - MIN_MAP_WIDTH - splitterCount * 7);
}

function clampPanelWidths(changedSide) {
  const available = availablePanelSpace();
  if (window.matchMedia("(max-width: 900px)").matches) {
    panelWidths.left = Math.min(panelWidths.left, available);
    return;
  }
  if (changedSide === "left") {
    panelWidths.left = Math.min(panelWidths.left, Math.max(0, available - panelWidths.right));
  } else {
    panelWidths.right = Math.min(panelWidths.right, Math.max(0, available - panelWidths.left));
  }
}

function setupSplitter(id, side) {
  const splitter = document.getElementById(id);
  splitter.addEventListener("pointerdown", (event) => {
    const startX = event.clientX;
    const startWidth = panelWidths[side];
    splitter.setPointerCapture(event.pointerId);
    splitter.classList.add("dragging");

    const move = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      panelWidths[side] = Math.max(0, startWidth + (side === "left" ? delta : -delta));
      clampPanelWidths(side);
      applyPanelWidths();
      render();
    };
    const stop = () => {
      splitter.classList.remove("dragging");
      splitter.removeEventListener("pointermove", move);
      splitter.removeEventListener("pointerup", stop);
      splitter.removeEventListener("pointercancel", stop);
      savePanelWidths();
    };
    splitter.addEventListener("pointermove", move);
    splitter.addEventListener("pointerup", stop);
    splitter.addEventListener("pointercancel", stop);
  });
  splitter.addEventListener("dblclick", () => {
    panelWidths[side] = DEFAULT_PANEL_WIDTHS[side];
    clampPanelWidths(side);
    applyPanelWidths();
    savePanelWidths();
    render();
  });
}

applyPanelWidths();
clampPanelWidths("right");
applyPanelWidths();
setupSplitter("leftSplitter", "left");
setupSplitter("rightSplitter", "right");

const formatNumber = (value) => new Intl.NumberFormat("en-US").format(value);
const formatBytes = (value) => {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
};
const formatAge = (value) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds} seconds ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
};

function metersPerPixel() {
  return viewWidthMeters / Math.max(canvas.clientWidth, 1);
}

function screenToWorld(screenX, screenY) {
  const scale = metersPerPixel();
  return {
    x: center.x + (screenX - canvas.clientWidth / 2) * scale,
    y: center.y - (screenY - canvas.clientHeight / 2) * scale,
  };
}

function worldToScreen(worldX, worldY) {
  const scale = metersPerPixel();
  return {
    x: canvas.clientWidth / 2 + (worldX - center.x) / scale,
    y: canvas.clientHeight / 2 - (worldY - center.y) / scale,
  };
}

function chooseGridStep() {
  const target = viewWidthMeters / 9;
  const steps = [16, 32, 64, 128, 256, 512, 1024];
  return steps.find((step) => step >= target) || 2048;
}

function drawGrid() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const scale = metersPerPixel();
  const cell = state?.map?.cellSizeMeters || 64;

  context.fillStyle = "#0c110e";
  context.fillRect(0, 0, width, height);

  if (!layerVisibility.get("grid")) return;

  const minorPixels = cell / scale;
  const boundsA = screenToWorld(0, height);
  const boundsB = screenToWorld(width, 0);

  if (minorPixels >= 12) {
    context.beginPath();
    context.strokeStyle = "#26362c";
    context.lineWidth = 1;
    const firstX = Math.floor(boundsA.x / cell) * cell;
    const firstY = Math.floor(boundsA.y / cell) * cell;
    for (let x = firstX; x <= boundsB.x; x += cell) {
      const screen = worldToScreen(x, 0);
      context.moveTo(Math.round(screen.x) + 0.5, 0);
      context.lineTo(Math.round(screen.x) + 0.5, height);
    }
    for (let y = firstY; y <= boundsB.y; y += cell) {
      const screen = worldToScreen(0, y);
      context.moveTo(0, Math.round(screen.y) + 0.5);
      context.lineTo(width, Math.round(screen.y) + 0.5);
    }
    context.stroke();
  }

  const major = chooseGridStep();
  context.beginPath();
  context.strokeStyle = "#4a6252";
  context.lineWidth = 1;
  const firstMajorX = Math.floor(boundsA.x / major) * major;
  const firstMajorY = Math.floor(boundsA.y / major) * major;
  for (let x = firstMajorX; x <= boundsB.x; x += major) {
    const screen = worldToScreen(x, 0);
    context.moveTo(Math.round(screen.x) + 0.5, 0);
    context.lineTo(Math.round(screen.x) + 0.5, height);
  }
  for (let y = firstMajorY; y <= boundsB.y; y += major) {
    const screen = worldToScreen(0, y);
    context.moveTo(0, Math.round(screen.y) + 0.5);
    context.lineTo(width, Math.round(screen.y) + 0.5);
  }
  context.stroke();

  const origin = worldToScreen(0, 0);
  context.strokeStyle = "#9fcf82";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(origin.x - 8, origin.y);
  context.lineTo(origin.x + 8, origin.y);
  context.moveTo(origin.x, origin.y - 8);
  context.lineTo(origin.x, origin.y + 8);
  context.stroke();
}

function drawWater() {
  if (!layerVisibility.get("terrain-regions")) return;
  const water = state?.map?.water;
  if (water?.status !== "available") return;
  const cell = state.map.cellSizeMeters;
  context.save();
  context.fillStyle = "rgb(42 112 153 / 68%)";
  for (const [cellX, cellY] of water.cells) {
    const bottomLeft = worldToScreen(cellX * cell, cellY * cell);
    const topRight = worldToScreen((cellX + 1) * cell, (cellY + 1) * cell);
    context.fillRect(bottomLeft.x, topRight.y, topRight.x - bottomLeft.x, bottomLeft.y - topRight.y);
  }
  context.restore();
}

function drawTerrainCells(stateKey, color) {
  if (!layerVisibility.get("terrain-regions")) return;
  const terrain = state?.map?.[stateKey];
  if (terrain?.status !== "available") return;
  const cell = state.map.cellSizeMeters;
  context.save();
  context.fillStyle = color;
  for (const [cellX, cellY] of terrain.cells) {
    const bottomLeft = worldToScreen(cellX * cell, cellY * cell);
    const topRight = worldToScreen((cellX + 1) * cell, (cellY + 1) * cell);
    context.fillRect(
      bottomLeft.x,
      topRight.y,
      topRight.x - bottomLeft.x,
      bottomLeft.y - topRight.y,
    );
  }
  context.restore();
}

function drawWorldBounds() {
  const bounds = state?.map?.worldBounds;
  if (!bounds) return;
  const cell = state.map.cellSizeMeters;
  const bottomLeft = worldToScreen(bounds.xMin * cell, bounds.yMin * cell);
  const topRight = worldToScreen((bounds.xMax + 1) * cell, (bounds.yMax + 1) * cell);
  context.save();
  context.strokeStyle = "#d9b65d";
  context.lineWidth = 2;
  context.setLineDash([8, 6]);
  context.strokeRect(
    bottomLeft.x,
    topRight.y,
    topRight.x - bottomLeft.x,
    bottomLeft.y - topRight.y,
  );
  context.restore();
}

function drawRoads() {
  if (!layerVisibility.get("roads")) return;
  const roads = state?.map?.roads;
  if (roads?.status !== "available") return;
  const cell = state.map.cellSizeMeters;
  const scale = metersPerPixel();
  const visibleMin = screenToWorld(0, canvas.clientHeight);
  const visibleMax = screenToWorld(canvas.clientWidth, 0);
  const segments = [];

  for (const [cellX, cellY, flags] of roads.cells) {
    const x = cellX * cell;
    const y = cellY * cell;
    if (
      x + cell < visibleMin.x ||
      x > visibleMax.x ||
      y + cell < visibleMin.y ||
      y > visibleMax.y
    ) {
      continue;
    }
    const center = worldToScreen(x + cell / 2, y + cell / 2);
    if (flags & 1) segments.push([center, worldToScreen(x + cell, y + cell / 2)]);
    if (flags & 2) segments.push([center, worldToScreen(x + cell / 2, y + cell)]);
    if (flags & 4) segments.push([center, worldToScreen(x, y + cell / 2)]);
    if (flags & 8) segments.push([center, worldToScreen(x + cell / 2, y)]);
  }

  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";
  for (const [color, width] of [
    ["#302b24", Math.max(5, 10 / Math.sqrt(scale))],
    ["#d8bd82", Math.max(2, 6 / Math.sqrt(scale))],
  ]) {
    context.beginPath();
    context.strokeStyle = color;
    context.lineWidth = width;
    for (const [from, to] of segments) {
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
    }
    context.stroke();
  }
  context.restore();
}

function featureBounds(feature) {
  if (feature.kind === "spawn") {
    const radius = Math.max(8 * metersPerPixel(), 12);
    return {
      xMin: feature.x - radius,
      xMax: feature.x + radius,
      yMin: feature.y - radius,
      yMax: feature.y + radius,
    };
  }
  const size = Math.max(feature.sizeCells || 1, 1) * state.map.cellSizeMeters;
  return {
    xMin: feature.cellX * state.map.cellSizeMeters,
    xMax: feature.cellX * state.map.cellSizeMeters + size,
    yMin: feature.cellY * state.map.cellSizeMeters,
    yMax: feature.cellY * state.map.cellSizeMeters + size,
  };
}

function drawFeatures() {
  const features = state?.map?.features || [];
  const scale = metersPerPixel();
  context.save();
  for (const feature of features) {
    const featureLayer = feature.mapLayer || "anchors";
    if (!layerVisibility.get(featureLayer)) continue;
    const screen = worldToScreen(feature.x, feature.y);
    if (feature.kind === "spawn") {
      context.fillStyle = "#f2f0a1";
      context.strokeStyle = "#111613";
      context.lineWidth = 2;
      context.beginPath();
      context.moveTo(screen.x, screen.y - 10);
      context.lineTo(screen.x + 8, screen.y + 8);
      context.lineTo(screen.x - 8, screen.y + 8);
      context.closePath();
      context.fill();
      context.stroke();
    } else {
      const pixelSize = Math.max(
        (feature.sizeCells * state.map.cellSizeMeters) / scale,
        8,
      );
      const featureColors = {
        "warehouse-schematics": ["rgb(86 168 232 / 35%)", "#56a8e8"],
        "builder-quests": ["rgb(242 201 76 / 35%)", "#f2c94c"],
        "chemical-oil-pits": ["rgb(155 89 232 / 35%)", "#9b59e8"],
        "underground-entrances": ["rgb(167 126 214 / 35%)", "#c49aef"],
      };
      const [fillColor, strokeColor] = featureColors[featureLayer]
        || ["rgb(159 207 130 / 30%)", "#9fcf82"];
      context.fillStyle = fillColor;
      context.strokeStyle = strokeColor;
      context.lineWidth = 2;
      if (feature.renderShape === "circle") {
        context.beginPath();
        context.arc(screen.x, screen.y, pixelSize / 2, 0, Math.PI * 2);
        context.fill();
        context.stroke();
      } else {
        context.fillRect(
          screen.x - pixelSize / 2,
          screen.y - pixelSize / 2,
          pixelSize,
          pixelSize,
        );
        context.strokeRect(
          screen.x - pixelSize / 2,
          screen.y - pixelSize / 2,
          pixelSize,
          pixelSize,
        );
        if (feature.tile && viewWidthMeters <= 1000) {
          drawTileSchematic(feature, screen, pixelSize);
        }
      }
    }
    if (viewWidthMeters <= 2000) {
      context.font = "12px Segoe UI";
      context.fillStyle = "#e1e9e3";
      context.textAlign = "center";
      context.fillText(feature.title, screen.x, screen.y - 14);
    }
  }
  context.restore();
}

function drawPrisonerCamps() {
  if (!layerVisibility.get("prisoner-camps")) return;
  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";
  for (const [cellX, cellY] of state?.map?.roads?.prisonerCampCells || []) {
    const screen = worldToScreen(
      (cellX + 0.5) * state.map.cellSizeMeters,
      (cellY + 0.5) * state.map.cellSizeMeters,
    );
    const segments = [
      [-4, -9, -6, 9],
      [5, -9, 3, 9],
      [-9, -3, 9, -3],
      [-9, 4, 9, 4],
    ];
    for (const [x1, y1, x2, y2] of segments) {
      context.beginPath();
      context.moveTo(screen.x + x1, screen.y + y1);
      context.lineTo(screen.x + x2, screen.y + y2);
      context.strokeStyle = "#24160b";
      context.lineWidth = 6;
      context.stroke();
      context.strokeStyle = "#ff9418";
      context.lineWidth = 3;
      context.stroke();
    }
  }
  context.restore();
}

function drawRuins() {
  if (!layerVisibility.get("ruins")) return;
  context.save();
  context.fillStyle = "#9fb7c4";
  context.strokeStyle = "#172027";
  context.lineWidth = 3;
  context.lineJoin = "round";
  for (const [cellX, cellY] of state?.map?.roads?.ruinCells || []) {
    const screen = worldToScreen(
      (cellX + 0.5) * state.map.cellSizeMeters,
      (cellY + 0.5) * state.map.cellSizeMeters,
    );
    context.beginPath();
    context.moveTo(screen.x - 10, screen.y + 8);
    context.lineTo(screen.x - 10, screen.y - 7);
    context.lineTo(screen.x - 4, screen.y - 7);
    context.lineTo(screen.x - 4, screen.y - 1);
    context.lineTo(screen.x + 1, screen.y - 5);
    context.lineTo(screen.x + 5, screen.y - 1);
    context.lineTo(screen.x + 10, screen.y - 7);
    context.lineTo(screen.x + 10, screen.y + 8);
    context.closePath();
    context.fill();
    context.stroke();
  }
  context.restore();
}

function drawMarkers() {
  if (!layerVisibility.get("notes")) return;
  context.save();
  for (const marker of state?.map?.markers || []) {
    const screen = worldToScreen(marker.x, marker.y);
    context.fillStyle = marker.color;
    context.strokeStyle = "#111613";
    context.lineWidth = 2;
    context.beginPath();
    context.arc(screen.x, screen.y, 7, 0, Math.PI * 2);
    context.fill();
    context.stroke();
    if (viewWidthMeters <= 3000) {
      context.font = "12px Segoe UI";
      context.textAlign = "center";
      context.fillStyle = "#e1e9e3";
      context.fillText(marker.title, screen.x, screen.y - 12);
    }
  }
  context.restore();
}

function drawPhysicalBeacons() {
  if (!layerVisibility.get("beacons")) return;
  const beacons = state?.map?.physicalBeacons?.beacons || [];
  context.save();
  for (const beacon of beacons) {
    if (beacon.worldId !== 1) continue;
    const screen = worldToScreen(beacon.x, beacon.y);
    context.translate(screen.x, screen.y);
    context.rotate(Math.PI / 4);
    context.fillStyle = beacon.color;
    context.strokeStyle = "#080b09";
    context.lineWidth = 2;
    context.fillRect(-7, -7, 14, 14);
    context.strokeRect(-7, -7, 14, 14);
    context.rotate(-Math.PI / 4);
    context.translate(-screen.x, -screen.y);
    if (viewWidthMeters <= 3000) {
      context.font = "12px Segoe UI";
      context.textAlign = "center";
      context.fillStyle = "#e1e9e3";
      context.fillText(beacon.iconName, screen.x, screen.y - 14);
    }
  }
  context.restore();
}

function drawVehicles() {
  if (!layerVisibility.get("vehicles")) return;
  const vehicles = state?.map?.vehicles?.vehicles || [];
  context.save();
  for (const vehicle of vehicles) {
    const screen = worldToScreen(vehicle.x, vehicle.y);
    context.fillStyle = vehicle.isRescueVehicle ? "#eb5757" : "#f2b84b";
    context.strokeStyle = "#171109";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(screen.x, screen.y - 9);
    context.lineTo(screen.x + 9, screen.y);
    context.lineTo(screen.x, screen.y + 9);
    context.lineTo(screen.x - 9, screen.y);
    context.closePath();
    context.fill();
    context.stroke();
    if (viewWidthMeters <= 3000) {
      context.font = "12px Segoe UI";
      context.textAlign = "center";
      context.fillStyle = vehicle.isRescueVehicle ? "#ffb5b5" : "#ffe5ad";
      context.fillText(vehicle.details, screen.x, screen.y - 14);
    }
  }
  context.restore();
}

function drawPlayer() {
  const player = state?.playerPosition?.player;
  if (!layerVisibility.get("player") || !player || player.worldId !== 1) return;
  const screen = worldToScreen(player.x, player.y);
  context.save();
  context.fillStyle = "#56ccf2";
  context.strokeStyle = "#071014";
  context.lineWidth = 3;
  context.beginPath();
  context.arc(screen.x, screen.y, 9, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  context.fillStyle = "#071014";
  context.beginPath();
  context.arc(screen.x, screen.y, 3, 0, Math.PI * 2);
  context.fill();
  if (viewWidthMeters <= 3000) {
    context.font = "bold 12px Segoe UI";
    context.textAlign = "center";
    context.fillStyle = "#dff8ff";
    context.fillText("Last saved player position", screen.x, screen.y - 15);
  }
  context.restore();
}

function rotateTilePoint(x, y, rotation) {
  let result = { x, y };
  const steps = Number.isInteger(rotation) ? rotation % 4 : 0;
  for (let step = 0; step < steps; step += 1) {
    result = { x: 1 - result.y, y: result.x };
  }
  return result;
}

function drawTileSchematic(feature, screen, pixelSize) {
  const tile = feature.tile;
  const widthMeters = Math.max(tile.cellsX || feature.sizeCells, 1) * state.map.cellSizeMeters;
  const heightMeters = Math.max(tile.cellsY || feature.sizeCells, 1) * state.map.cellSizeMeters;
  const colors = {
    assets: "#7f9d78",
    blueprints: "#e2c878",
    harvestables: "#68b66b",
    kinematics: "#d98262",
    nodes: "#8ca4bf",
    prefabs: "#c48cce",
  };
  context.save();
  context.beginPath();
  context.rect(
    screen.x - pixelSize / 2,
    screen.y - pixelSize / 2,
    pixelSize,
    pixelSize,
  );
  context.clip();
  for (const point of tile.schematicPoints || []) {
    const normalized = rotateTilePoint(
      Math.max(0, Math.min(1, point.x / widthMeters)),
      Math.max(0, Math.min(1, point.y / heightMeters)),
      feature.rotation,
    );
    context.fillStyle = colors[point.category] || "#d7ded9";
    context.globalAlpha = point.category === "nodes" ? 0.45 : 0.85;
    context.beginPath();
    context.arc(
      screen.x - pixelSize / 2 + normalized.x * pixelSize,
      screen.y + pixelSize / 2 - normalized.y * pixelSize,
      point.category === "blueprints" || point.category === "prefabs" ? 2.4 : 1.4,
      0,
      Math.PI * 2,
    );
    context.fill();
  }
  context.restore();
}

function updateScale() {
  const candidates = [10, 20, 50, 100, 200, 500, 1000];
  const maxMeters = viewWidthMeters * 0.22;
  const value = [...candidates].reverse().find((item) => item <= maxMeters) || 10;
  const pixels = value / metersPerPixel();
  const scale = document.querySelector("#scaleBar span");
  scale.style.width = `${pixels}px`;
  document.querySelector("#scaleBar label").textContent =
    value >= 1000 ? `${value / 1000} km` : `${value} m`;
}

function render() {
  const ratio = window.devicePixelRatio || 1;
  const width = Math.floor(canvas.clientWidth * ratio);
  const height = Math.floor(canvas.clientHeight * ratio);
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  drawGrid();
  drawTerrainCells("desert", "rgb(196 157 83 / 54%)");
  drawTerrainCells("burntForest", "rgb(104 68 54 / 68%)");
  drawTerrainCells("autumnForest", "rgb(193 132 184 / 52%)");
  drawWater();
  drawWorldBounds();
  drawRoads();
  drawFeatures();
  drawRuins();
  drawPrisonerCamps();
  drawPhysicalBeacons();
  drawVehicles();
  drawMarkers();
  drawPlayer();
  document.getElementById("zoomReadout").textContent =
    `Visible width: ${viewWidthMeters >= 1000 ? `${viewWidthMeters / 1000} km` : `${viewWidthMeters} m`}`;
  updateScale();
}

function setZoom(nextWidth, anchorX = canvas.clientWidth / 2, anchorY = canvas.clientHeight / 2) {
  const anchorBefore = screenToWorld(anchorX, anchorY);
  viewWidthMeters = Math.max(100, Math.min(10000, nextWidth));
  const anchorAfter = screenToWorld(anchorX, anchorY);
  center.x += anchorBefore.x - anchorAfter.x;
  center.y += anchorBefore.y - anchorAfter.y;
  render();
}

function nearestPreset(direction) {
  const index = presets.findIndex((item) => item >= viewWidthMeters);
  if (direction < 0) {
    return presets[Math.max(0, (index < 0 ? presets.length : index) - 1)];
  }
  return presets[Math.min(presets.length - 1, Math.max(0, index + (presets[index] === viewWidthMeters ? 1 : 0)))];
}

function defaultMapCenter() {
  const spawn = state?.map?.features?.find((feature) => feature.kind === "spawn");
  return spawn ? { x: spawn.x, y: spawn.y } : { x: 0, y: 0 };
}

function fitWorld() {
  const bounds = state?.map?.worldBounds;
  if (!bounds) return;
  const cell = state.map.cellSizeMeters;
  center = {
    x: ((bounds.xMin + bounds.xMax + 1) * cell) / 2,
    y: ((bounds.yMin + bounds.yMax + 1) * cell) / 2,
  };
  const worldWidth = (bounds.xMax - bounds.xMin + 1) * cell;
  const worldHeight = (bounds.yMax - bounds.yMin + 1) * cell;
  const aspect = Math.max(canvas.clientWidth / Math.max(canvas.clientHeight, 1), 1);
  setZoom(Math.max(worldWidth, worldHeight * aspect) * 1.06);
}

function addDetail(term, value) {
  const list = document.getElementById("saveDetails");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = value;
  list.append(dt, dd);
}

function populateInterface() {
  const save = state.save;
  const selectedSaveDetails = document.getElementById("selectedSaveDetails");
  const selectedSaveStorageKey = "jc-scrapmap-selected-save-open";
  selectedSaveDetails.open = sessionStorage.getItem(selectedSaveStorageKey) === "true";
  selectedSaveDetails.addEventListener("toggle", () => {
    sessionStorage.setItem(selectedSaveStorageKey, String(selectedSaveDetails.open));
  });
  document.getElementById("selectedSaveSummary").textContent =
    `Selected save · ${save.filename} · seed ${save.seed}`;
  document.getElementById("subtitle").textContent =
    `${save.filename} · seed ${save.seed}`;
  addDetail("File", save.filename);
  addDetail("Version", save.savegameVersion);
  addDetail("Seed", formatNumber(save.seed));
  addDetail("Game tick", formatNumber(save.gameTick));
  addDetail("Size", formatBytes(save.sizeBytes));
  addDetail("Worlds", save.worldIds.join(", "));
  addDetail("Map ID", save.identity);
  addDetail("Read-only", save.readOnlyVerified ? "Verified" : "Not verified");
  const player = state.playerPosition?.player;
  if (player) {
    addDetail(
      "Saved player",
      `X ${player.x.toFixed(1)} · Y ${player.y.toFixed(1)} · Z ${player.z.toFixed(1)}`,
    );
    addDetail("Player cell", `${player.cellX}, ${player.cellY} · world ${player.worldId}`);
    addDetail("Position saved", new Date(state.playerPosition.savedUtc).toLocaleString());
  }

  const layers = document.getElementById("layers");
  state.layers.forEach((layer) => {
    layerVisibility.set(layer.id, layer.visible && layer.available);
    const label = document.createElement("label");
    label.className = `layer${layer.available ? "" : " unavailable"}`;
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = layer.visible;
    input.disabled = !layer.available;
    input.addEventListener("change", () => {
      layerVisibility.set(layer.id, input.checked);
      render();
    });
    label.append(input, document.createTextNode(layer.label));
    layers.append(label);
  });

  const playerMessage = player && player.worldId !== 1
    ? `Last saved player position is in world ${player.worldId}; it is not drawn on the overworld.`
    : state.playerPosition.message;
  document.getElementById("playerStatus").textContent =
    `${playerMessage} Save file updated ${formatAge(state.playerPosition.savedUtc)}.`;
  document.getElementById("centerPlayer").hidden = !player || player.worldId !== 1;
  document.getElementById("mapStatus").textContent = state.map.message;
  const roadsStatus = state.map.roads;
  if (roadsStatus?.status !== "available") {
    document.getElementById("mapStatus").textContent =
      `${state.map.message} ${roadsStatus.message}`;
    document.getElementById("mapStatus").classList.add("warning");
  }

  const diagnostics = document.getElementById("diagnosticsList");
  state.diagnostics.forEach((item) => {
    const entry = document.createElement("div");
    entry.className = `diagnostic ${item.level === "ok" ? "" : item.level}`;
    entry.textContent = item.message;
    diagnostics.append(entry);
  });

  const saveList = document.getElementById("saveList");
  state.availableSaves.forEach((item) => {
    const entry = document.createElement("div");
    entry.className = `save-item${item.selected ? " selected" : ""}`;
    entry.tabIndex = item.selected ? -1 : 0;
    entry.setAttribute("role", item.selected ? "status" : "button");
    const title = document.createElement("div");
    title.textContent = item.filename;
    const details = document.createElement("div");
    details.className = "small";
    details.textContent =
      `seed ${formatNumber(item.seed)} · ${formatBytes(item.sizeBytes)} · ${new Date(item.modifiedUtc).toLocaleString()}`;
    entry.append(title, details);
    if (!item.selected) {
      const select = async () => {
        if (switchingSave) return;
        switchingSave = true;
        entry.classList.add("switching");
        details.textContent = "Opening read-only and verifying…";
        try {
          const response = await fetch("../api/select-save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identity: item.identity }),
          });
          const result = await response.json();
          if (!response.ok || !result.ok) {
            throw new Error(result.error || `HTTP ${response.status}`);
          }
          window.location.reload();
        } catch (error) {
          switchingSave = false;
          entry.classList.remove("switching");
          details.textContent = `Could not switch: ${error.message}`;
        }
      };
      entry.addEventListener("click", select);
      entry.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
    }
    saveList.append(entry);
  });

  const underground = state.underground;
  const undergroundSummary = document.getElementById("undergroundSummary");
  const undergroundFloors = document.getElementById("undergroundFloors");
  if (underground?.status === "available") {
    const nextProgress = underground.nextVaultTarget
      ? `Next access card: ${formatNumber(underground.vaultTotal)} / ${formatNumber(underground.nextVaultTarget)} Vault value (${formatNumber(underground.vaultRemaining)} remaining).`
      : `Vault value: ${formatNumber(underground.vaultTotal)}. All Vault access cards recorded.`;
    undergroundSummary.textContent =
      `Vault: ${formatNumber(underground.vaultTotal)} · Access card ${underground.ownedCards.at(-1) || 0}. ${nextProgress}`;
    underground.floors.forEach((floor) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "underground-floor";
      button.disabled = !floor.generated;
      const title = document.createElement("strong");
      title.textContent = `Level ${floor.depth}: ${floor.name}`;
      const status = document.createElement("span");
      status.className = "underground-floor-status";
      const access = floor.accessible ? "Accessible" : `Locked${floor.vaultTarget ? ` · Vault ${formatNumber(floor.vaultTarget)}` : ""}`;
      const generated = floor.generated ? `world ${floor.worldId}` : "not generated in this save";
      status.textContent = `${access}${floor.reached ? " · reached" : ""} · ${generated}`;
      button.append(title, status);
      if (floor.generated) {
        button.addEventListener("click", () => {
          window.open(`underground.html?depth=${floor.depth}`, "_blank", "noopener");
        });
      }
      undergroundFloors.append(button);
    });
  } else {
    undergroundSummary.textContent = underground?.message || "Underground progression is unavailable.";
  }

  const specialMaps = document.getElementById("specialMaps");
  const island = state.excavationIsland;
  const islandButton = document.createElement("button");
  islandButton.type = "button";
  islandButton.className = "underground-floor";
  islandButton.disabled = island?.status !== "available";
  const islandTitle = document.createElement("strong");
  islandTitle.textContent = "Excavation Island";
  const islandStatus = document.createElement("span");
  islandStatus.className = "underground-floor-status";
  islandStatus.textContent = island?.status === "available"
    ? `Surface map · ${formatNumber(island.summary.schematicPoints)} authored points`
    : (island?.message || "Map unavailable");
  islandButton.append(islandTitle, islandStatus);
  if (island?.status === "available") {
    islandButton.addEventListener("click", () => {
      window.open("excavation.html", "_blank", "noopener");
    });
  }
  specialMaps.append(islandButton);
}

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const factor = event.deltaY > 0 ? 1.22 : 1 / 1.22;
  setZoom(viewWidthMeters * factor, event.offsetX, event.offsetY);
}, { passive: false });

canvas.addEventListener("pointerdown", (event) => {
  dragging = true;
  dragStart = { x: event.clientX, y: event.clientY, centerX: center.x, centerY: center.y };
  canvas.classList.add("dragging");
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  const rect = canvas.getBoundingClientRect();
  const world = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
  document.getElementById("coordinateReadout").textContent =
    `X ${world.x.toFixed(1)} · Y ${world.y.toFixed(1)}`;
  if (!dragging) return;
  const scale = metersPerPixel();
  center.x = dragStart.centerX - (event.clientX - dragStart.x) * scale;
  center.y = dragStart.centerY + (event.clientY - dragStart.y) * scale;
  render();
});

canvas.addEventListener("pointerup", () => {
  dragging = false;
  canvas.classList.remove("dragging");
});

canvas.addEventListener("click", (event) => {
  if (!state) return;
  const rect = canvas.getBoundingClientRect();
  const world = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
  const marker = [...(state.map.markers || [])].reverse().find((item) => {
    if (!layerVisibility.get("notes")) return false;
    const screen = worldToScreen(item.x, item.y);
    return Math.hypot(screen.x - (event.clientX - rect.left), screen.y - (event.clientY - rect.top)) <= 12;
  });
  if (marker) {
    hideInstantRecovery();
    openMarkerForm(marker.x, marker.y, marker);
    return;
  }
  const vehicle = [...(state.map.vehicles?.vehicles || [])].reverse().find((item) => {
    if (!layerVisibility.get("vehicles")) return false;
    const screen = worldToScreen(item.x, item.y);
    return Math.hypot(screen.x - (event.clientX - rect.left), screen.y - (event.clientY - rect.top)) <= 12;
  });
  if (vehicle) {
    selectedFeature = null;
    selectedVehicle = vehicle;
    document.getElementById("mapStatus").textContent =
      `Vehicle saved at X ${vehicle.x.toFixed(1)} · Y ${vehicle.y.toFixed(1)}. ${vehicle.details}. ${vehicle.bodyCount} connected bod${vehicle.bodyCount === 1 ? "y" : "ies"}.`;
    document.getElementById("discoveryButton").hidden = true;
    document.getElementById("excavationMapButton").hidden = true;
    const recoveryDetails = document.getElementById("instantRecoveryDetails");
    recoveryDetails.hidden = false;
    recoveryDetails.open = false;
    return;
  }
  const feature = [...(state.map.features || [])].reverse().find((item) => {
    const featureLayer = item.mapLayer || "anchors";
    if (!layerVisibility.get(featureLayer)) return false;
    const bounds = featureBounds(item);
    return (
      world.x >= bounds.xMin &&
      world.x <= bounds.xMax &&
      world.y >= bounds.yMin &&
      world.y <= bounds.yMax
    );
  });
  if (!feature) {
    hideInstantRecovery();
    return;
  }
  hideInstantRecovery();
  selectedFeature = feature;
  const road =
    feature.roadRequired === null || feature.roadRequired === undefined
      ? ""
      : ` Road connection: ${feature.roadRequired ? "required" : "not required"}.`;
  const tile = feature.tile;
  const tileDetails = tile
    ? ` Developer label: ${feature.developerLabel}. Tile: ${tile.developerTile} (${tile.cellsX}×${tile.cellsY} cells, UUID ${tile.uuid}). Entities: ${Object.entries(tile.entityCounts)
        .map(([name, count]) => `${name} ${count}`)
        .join(", ")}. Schematic uses installed entity positions and is not a screenshot.`
    : "";
  const undergroundDetails = feature.undergroundEntrance
    ? ` ${feature.undergroundMessage}`
    : "";
  document.getElementById("mapStatus").textContent =
    `${feature.title} · cell ${feature.cellX}, ${feature.cellY}. Visibility: generator-known; discovery ${feature.discoveryStatus} (${feature.discoverySource || "unconfirmed"}). ${feature.discoveryEvidence?.reason || ""} ${feature.details}${road}${tileDetails}${undergroundDetails} Placement source: ${feature.source}.`;
  const discoveryButton = document.getElementById("discoveryButton");
  document.getElementById("excavationMapButton").hidden = !(
    feature.excavationIslandMap && state.excavationIsland?.status === "available"
  );
  if (feature.kind === "spawn") {
    discoveryButton.hidden = true;
  } else {
    discoveryButton.hidden = false;
    discoveryButton.textContent =
      feature.discoveryStatus === "discovered"
        ? "Mark undiscovered"
        : "Mark discovered";
  }
});

function openMarkerForm(x, y, marker = null) {
  hideInstantRecovery();
  editingMarker = marker;
  markerPosition = { x, y };
  document.getElementById("markerTitle").value = marker?.title || "";
  document.getElementById("markerCategory").value = marker?.category || "note";
  document.getElementById("markerColor").value = marker?.color || "#f2c94c";
  document.getElementById("markerNote").value = marker?.note || "";
  document.getElementById("deleteMarkerButton").hidden = !marker;
  document.getElementById("markerForm").hidden = false;
  document.getElementById("markerTitle").focus();
  document.getElementById("mapStatus").textContent =
    `${marker ? "Editing" : "New"} custom note at X ${x.toFixed(1)}, Y ${y.toFixed(1)}.`;
}

function closeMarkerForm() {
  editingMarker = null;
  markerPosition = null;
  document.getElementById("markerForm").hidden = true;
}

function hideInstantRecovery() {
  selectedVehicle = null;
  const details = document.getElementById("instantRecoveryDetails");
  details.hidden = true;
  details.open = false;
  document.getElementById("recoveryButton").disabled = false;
}

async function markerRequest(path, payload) {
  if (state?.save?.identity) {
    sessionStorage.setItem(
      `jc-scrapmap-view-${state.save.identity}`,
      JSON.stringify({ center, viewWidthMeters }),
    );
  }
  const response = await fetch(`..${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) throw new Error(result.error || `HTTP ${response.status}`);
  window.location.reload();
}

document.getElementById("newMarkerButton").addEventListener("click", () => {
  openMarkerForm(center.x, center.y);
});

canvas.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  if (!state) return;
  const rect = canvas.getBoundingClientRect();
  const world = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
  openMarkerForm(world.x, world.y);
});

document.getElementById("markerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  try {
    await markerRequest("/api/save-marker", {
      id: editingMarker?.id,
      x: markerPosition.x,
      y: markerPosition.y,
      title: document.getElementById("markerTitle").value,
      category: document.getElementById("markerCategory").value,
      color: document.getElementById("markerColor").value,
      note: document.getElementById("markerNote").value,
    });
  } catch (error) {
    submit.disabled = false;
    document.getElementById("mapStatus").textContent = `Could not save note: ${error.message}`;
  }
});

document.getElementById("deleteMarkerButton").addEventListener("click", async () => {
  if (!editingMarker || !window.confirm(`Delete “${editingMarker.title}”?`)) return;
  try {
    await markerRequest("/api/delete-marker", { id: editingMarker.id });
  } catch (error) {
    document.getElementById("mapStatus").textContent = `Could not delete note: ${error.message}`;
  }
});

document.getElementById("cancelMarkerButton").addEventListener("click", closeMarkerForm);

document.getElementById("discoveryButton").addEventListener("click", async () => {
  if (!selectedFeature) return;
  const button = document.getElementById("discoveryButton");
  button.disabled = true;
  const discovered = selectedFeature.discoveryStatus !== "discovered";
  try {
    const response = await fetch("../api/set-discovery", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        featureId: selectedFeature.id,
        discovered,
      }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    window.location.reload();
  } catch (error) {
    button.disabled = false;
    document.getElementById("mapStatus").textContent =
      `Could not update discovery state: ${error.message}`;
  }
});

document.getElementById("recoveryButton").addEventListener("click", async () => {
  if (!selectedVehicle || !state?.save?.identity) return;
  const button = document.getElementById("recoveryButton");
  button.disabled = true;
  sessionStorage.setItem(
    `jc-scrapmap-view-${state.save.identity}`,
    JSON.stringify({ center, viewWidthMeters }),
  );
  try {
    const response = await fetch("../api/recover-vehicle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identity: state.save.identity,
        vehicleId: selectedVehicle.id,
      }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    window.location.reload();
  } catch (error) {
    button.disabled = false;
    document.getElementById("mapStatus").textContent =
      `Could not recover vehicle: ${error.message}`;
  }
});

document.getElementById("excavationMapButton").addEventListener("click", () => {
  window.open("excavation.html", "_blank", "noopener");
});

document.getElementById("zoomIn").addEventListener("click", () => setZoom(nearestPreset(-1)));
document.getElementById("zoomOut").addEventListener("click", () => setZoom(nearestPreset(1)));
document.getElementById("centerMap").addEventListener("click", () => {
  center = defaultMapCenter();
  render();
});
document.getElementById("centerPlayer").addEventListener("click", () => {
  const player = state?.playerPosition?.player;
  if (!player || player.worldId !== 1) return;
  center = { x: player.x, y: player.y };
  render();
});

document.getElementById("fitWorld").addEventListener("click", fitWorld);
window.addEventListener("resize", () => {
  clampPanelWidths("right");
  applyPanelWidths();
  render();
});

fetch("../generated/state.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((loadedState) => {
    state = loadedState;
    const savedView = sessionStorage.getItem(`jc-scrapmap-view-${state.save.identity}`);
    if (savedView) {
      try {
        const parsed = JSON.parse(savedView);
        if (
          Number.isFinite(parsed?.center?.x) &&
          Number.isFinite(parsed?.center?.y) &&
          Number.isFinite(parsed?.viewWidthMeters)
        ) {
          center = { x: parsed.center.x, y: parsed.center.y };
          viewWidthMeters = parsed.viewWidthMeters;
        } else {
          throw new Error("Invalid saved viewport.");
        }
      } catch {
        sessionStorage.removeItem(`jc-scrapmap-view-${state.save.identity}`);
        viewWidthMeters = state.map.zoomPresetsMeters.includes(1000) ? 1000 : 500;
        center = defaultMapCenter();
      }
    } else {
      viewWidthMeters = state.map.zoomPresetsMeters.includes(1000) ? 1000 : 500;
      center = defaultMapCenter();
    }
    populateInterface();
    render();
    const generatedUtc = state.app.generatedUtc;
    window.setInterval(async () => {
      try {
        const response = await fetch("../generated/state.json", { cache: "no-store" });
        if (!response.ok) return;
        const latest = await response.json();
        if (latest.app.generatedUtc !== generatedUtc) {
          sessionStorage.setItem(
            `jc-scrapmap-view-${state.save.identity}`,
            JSON.stringify({ center, viewWidthMeters }),
          );
          window.location.reload();
        }
      } catch {
        // Keep the current map usable if a refresh check temporarily fails.
      }
    }, 1000);
  })
  .catch((error) => {
    document.getElementById("subtitle").textContent = "State could not be loaded";
    document.getElementById("mapStatus").textContent =
      `Run the launcher to generate state.json. ${error.message}`;
    render();
  });
