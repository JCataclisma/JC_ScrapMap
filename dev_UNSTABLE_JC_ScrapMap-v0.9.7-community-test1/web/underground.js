"use strict";
const canvas = document.getElementById("undergroundCanvas");
const context = canvas.getContext("2d");
const details = document.getElementById("details");
const depth = Number(new URLSearchParams(window.location.search).get("depth"));
let floor = null;

function draw() {
  if (!floor) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(canvas.clientWidth * ratio);
  canvas.height = Math.floor(canvas.clientHeight * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.fillStyle = "#080b09";
  context.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  const resources = floor.resources || [];
  const bounds = [...floor.cells, ...floor.voxelCells, ...resources.map((item) => ({ x: item.cellX, y: item.cellY }))];
  if (!bounds.length) return;
  const minX = Math.min(...bounds.map((item) => item.x));
  const maxX = Math.max(...bounds.map((item) => item.x));
  const minY = Math.min(...bounds.map((item) => item.y));
  const maxY = Math.max(...bounds.map((item) => item.y));
  const width = maxX - minX + 1;
  const height = maxY - minY + 1;
  const size = Math.min((canvas.clientWidth - 50) / width, (canvas.clientHeight - 50) / height);
  const left = (canvas.clientWidth - width * size) / 2;
  const top = (canvas.clientHeight - height * size) / 2;
  const screenPoint = (mapX, mapY) => ({ x: left + (mapX - minX) * size, y: top + (maxY + 1 - mapY) * size });
  const authoredLookup = new Map(floor.cells.map((cell) => [`${cell.x},${cell.y}`, cell]));
  const voxelLookup = new Map(floor.voxelCells.map((cell) => [`${cell.x},${cell.y}`, cell]));

  for (let cellY = minY; cellY <= maxY; cellY += 1) {
    for (let cellX = minX; cellX <= maxX; cellX += 1) {
      const point = screenPoint(cellX, cellY + 1);
      const authored = authoredLookup.get(`${cellX},${cellY}`);
      context.fillStyle = authored ? (authored.authored ? "#405548" : "#202a24") : "#151d18";
      context.fillRect(point.x, point.y, Math.max(1, size - 1), Math.max(1, size - 1));
      const voxel = voxelLookup.get(`${cellX},${cellY}`);
      if (voxel) {
        context.fillStyle = "#87633b";
        context.beginPath();
        context.arc(point.x + size / 2, point.y + size / 2, Math.max(2, size * 0.12), 0, Math.PI * 2);
        context.fill();
      }
    }
  }

  const hitMarkers = resources.map((item) => {
    const point = screenPoint(item.mapX, item.mapY);
    const radius = Math.max(6, Math.min(12, size * 0.18));
    context.fillStyle = item.kind === "quartz" ? "#d8f4ff" : "#ee8b45";
    context.strokeStyle = item.kind === "quartz" ? "#65cce9" : "#ffd09b";
    context.lineWidth = 2;
    context.beginPath(); context.arc(point.x, point.y, radius, 0, Math.PI * 2); context.fill(); context.stroke();
    return { item, x: point.x, y: point.y, radius: radius + 5 };
  });

  canvas.onclick = (event) => {
    const marker = [...hitMarkers].reverse().find((hit) => Math.hypot(event.offsetX - hit.x, event.offsetY - hit.y) <= hit.radius);
    if (marker) {
      const item = marker.item;
      const material = item.material ? ` ${item.material}.` : "";
      const coordinates = item.worldX == null ? `Cell ${item.cellX}, ${item.cellY}` : `World ${item.worldX.toFixed(1)}, ${item.worldY.toFixed(1)} m`;
      details.textContent = `${item.name}.${material} ${item.quantityLabel}. Tool: ${item.tool}. ${coordinates}. ${item.positionAccuracy}.`;
      return;
    }
    const cellX = Math.floor((event.offsetX - left) / size) + minX;
    const cellY = maxY - Math.floor((event.offsetY - top) / size);
    const voxel = voxelLookup.get(`${cellX},${cellY}`);
    details.textContent = voxel ? `Cell ${cellX}, ${cellY}: ${voxel.recordCount} saved voxel-terrain record${voxel.recordCount === 1 ? "" : "s"}. Material inside voxel records is not decoded yet.` : `Cell ${cellX}, ${cellY}: no saved voxel-terrain changes.`;
  };
}

fetch("../generated/state.json", { cache: "no-store" }).then((response) => response.json()).then((state) => {
  floor = state.underground?.floors?.find((item) => item.depth === depth && item.generated);
  if (!floor) throw new Error("This floor is not generated in the selected save.");
  const summary = floor.resourceSummary || {};
  document.title = `JC ScrapMap · ${floor.name}`;
  document.getElementById("title").textContent = `Level ${floor.depth}: ${floor.name}`;
  document.getElementById("subtitle").textContent = `Saved world ${floor.worldId} · ${floor.accessible ? "accessible" : "locked"}${floor.reached ? " · reached" : ""} · ${summary.markers || 0} resource markers`;
  document.getElementById("vault").textContent = `Vault ${new Intl.NumberFormat("en-US").format(state.underground.vaultTotal)}`;
  details.textContent = `${summary.quartzFormations || 0} Quartz formations (${summary.quartzYield || 0} Quartz total) and ${summary.looseOreChunks || 0} loose ore chunks identified. Click a colored marker.`;
  draw();
}).catch((error) => { details.textContent = error.message; });
window.addEventListener("resize", draw);
