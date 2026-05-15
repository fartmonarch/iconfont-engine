#!/usr/bin/env node
/**
 * Visual Similarity Computation for Conflict Variants
 *
 * Renders each conflict variant as a bitmap and computes pixel overlap.
 *
 * Usage:
 *     node pipeline/_visual_similarity.js
 *
 * Input:
 *     report/conflict_records.json
 *     sources/phase4_glyphs/normalized_glyphs.json
 *
 * Output:
 *     report/visual_similarity_scores.json
 */
const fs = require('fs');
const path = require('path');
const { createCanvas, Path2D } = require('@napi-rs/canvas');

const DATA_DIR = path.dirname(__dirname);
const CONFLICTS_PATH = path.join(DATA_DIR, 'report', 'conflict_records.json');
const GLYPHS_PATH = path.join(DATA_DIR, 'sources', 'phase4_glyphs', 'normalized_glyphs.json');
const OUTPUT_PATH = path.join(DATA_DIR, 'report', 'visual_similarity_scores.json');

const RENDER_SIZE = 64;
const UPM = 1024;

function contourToSvgPath(contour) {
  if (!contour || contour.length === 0) return '';

  // Find first on-curve point
  let firstOn = -1;
  for (let i = 0; i < contour.length; i++) {
    if (contour[i].on_curve) {
      firstOn = i;
      break;
    }
  }

  if (firstOn === -1) {
    // All off-curve: insert implied on-curve points
    const pts = contour;
    const midX = (pts[pts.length - 1].x + pts[0].x) / 2;
    const midY = (pts[pts.length - 1].y + pts[0].y) / 2;
    let d = `M ${midX.toFixed(1)} ${midY.toFixed(1)} `;
    for (let i = 0; i < pts.length; i++) {
      const pt = pts[i];
      const nextPt = pts[(i + 1) % pts.length];
      if (i === pts.length - 1) {
        d += `Q ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} ${midX.toFixed(1)} ${midY.toFixed(1)} `;
      } else {
        const mid2X = (pt.x + nextPt.x) / 2;
        const mid2Y = (pt.y + nextPt.y) / 2;
        d += `Q ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} ${mid2X.toFixed(1)} ${mid2Y.toFixed(1)} `;
      }
    }
    d += 'Z';
    return d;
  }

  // Rotate to start with on-curve point
  const pts = contour.slice(firstOn).concat(contour.slice(0, firstOn));
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)} `;

  let i = 1;
  while (i < pts.length) {
    const pt = pts[i];
    if (pt.on_curve) {
      d += `L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} `;
      i++;
    } else {
      if (i + 1 < pts.length && pts[i + 1].on_curve) {
        d += `Q ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} ${pts[i + 1].x.toFixed(1)} ${pts[i + 1].y.toFixed(1)} `;
        i += 2;
      } else if (i + 1 < pts.length && !pts[i + 1].on_curve) {
        const midX = (pt.x + pts[i + 1].x) / 2;
        const midY = (pt.y + pts[i + 1].y) / 2;
        d += `Q ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} ${midX.toFixed(1)} ${midY.toFixed(1)} `;
        i++;
      } else {
        // Last point is off-curve, wrap to first
        const first = pts[0];
        const midX = (pt.x + first.x) / 2;
        const midY = (pt.y + first.y) / 2;
        d += `Q ${pt.x.toFixed(1)} ${pt.y.toFixed(1)} ${midX.toFixed(1)} ${midY.toFixed(1)} `;
        i++;
      }
    }
  }

  d += 'Z';
  return d;
}

function contoursToSvgPath(contours) {
  return contours.map(c => contourToSvgPath(c)).join(' ');
}

function renderGlyph(contours) {
  const canvas = createCanvas(RENDER_SIZE, RENDER_SIZE);
  const ctx = canvas.getContext('2d');
  const scale = RENDER_SIZE / UPM;

  ctx.save();
  ctx.translate(0, RENDER_SIZE);
  ctx.scale(scale, -scale);

  const pathStr = contoursToSvgPath(contours);
  const p = new Path2D(pathStr);
  ctx.fill(p);
  ctx.restore();

  return ctx.getImageData(0, 0, RENDER_SIZE, RENDER_SIZE);
}

function comparePixels(imgA, imgB) {
  const dataA = imgA.data;
  const dataB = imgB.data;
  let same = 0;
  const total = dataA.length / 4;

  for (let i = 0; i < dataA.length; i += 4) {
    // Compare alpha channel (filled or not)
    const a = dataA[i + 3] > 50;
    const b = dataB[i + 3] > 50;
    if (a === b) same++;
  }

  return total > 0 ? same / total : 1.0;
}

function main() {
  console.log('='.repeat(51));
  console.log('Visual Similarity Computation');
  console.log('='.repeat(51));
  console.log();

  console.log('Loading conflicts...');
  const conflicts = JSON.parse(fs.readFileSync(CONFLICTS_PATH, 'utf-8'));

  console.log('Loading normalized glyphs...');
  const glyphs = JSON.parse(fs.readFileSync(GLYPHS_PATH, 'utf-8'));
  const glyphMap = new Map();
  for (const g of glyphs) {
    const key = `${g.glyphHash}:${g.assetId}`;
    glyphMap.set(key, g);
  }
  console.log(`  Glyph entries: ${glyphMap.size}`);
  console.log();

  const records = conflicts.records.filter(r =>
    r.type === 'unicode_conflict' || r.type === 'name_conflict'
  );

  const result = {};
  let rendered = 0;

  console.log(`Processing ${records.length} conflict records...`);

  for (let ri = 0; ri < records.length; ri++) {
    const record = records[ri];
    const variants = record.variants;
    const key = record.key;

    // Render each variant
    const images = [];
    for (let vi = 0; vi < variants.length; vi++) {
      const v = variants[vi];
      let found = null;
      for (const src of v.sources || []) {
        const mapKey = `${v.glyphHash}:${src.assetId}`;
        if (glyphMap.has(mapKey)) {
          found = glyphMap.get(mapKey);
          break;
        }
      }

      if (!found) {
        // Try without assetId
        for (const [k, g] of glyphMap) {
          if (g.glyphHash === v.glyphHash) {
            found = g;
            break;
          }
        }
      }

      if (found && found.contours && found.contours.length > 0) {
        try {
          const img = renderGlyph(found.contours);
          images.push({ vi, img });
          rendered++;
        } catch (e) {
          console.log(`  [WARN] Render failed: ${key} v${vi}: ${e.message}`);
        }
      }
    }

    // Compare all pairs
    const scores = [];
    let maxScore = 0;
    let minScore = 1.0;
    let sumScore = 0;
    let pairCount = 0;
    for (let i = 0; i < images.length; i++) {
      for (let j = i + 1; j < images.length; j++) {
        const score = comparePixels(images[i].img, images[j].img);
        scores.push({
          variantA: images[i].vi,
          variantB: images[j].vi,
          score: parseFloat(score.toFixed(4)),
        });
        maxScore = Math.max(maxScore, score);
        minScore = Math.min(minScore, score);
        sumScore += score;
        pairCount++;
      }
    }

    result[key] = {
      type: record.type,
      maxScore: parseFloat(maxScore.toFixed(4)),
      minScore: pairCount > 0 ? parseFloat(minScore.toFixed(4)) : 0,
      avgScore: pairCount > 0 ? parseFloat((sumScore / pairCount).toFixed(4)) : 0,
      pairCount,
      scores,
    };

    if ((ri + 1) % 100 === 0) {
      console.log(`  Processed ${ri + 1}/${records.length}...`);
    }
  }

  console.log();
  console.log(`Rendered: ${rendered} glyphs`);

  // Distribution
  const allScores = Object.values(result).map(r => r.maxScore);
  console.log('Visual similarity distribution:');
  for (const t of [0.99, 0.95, 0.9, 0.85, 0.8, 0.7, 0.5]) {
    const c = allScores.filter(s => s >= t).length;
    console.log(`  >= ${t}: ${c}`);
  }

  console.log();
  console.log(`Writing: ${OUTPUT_PATH}`);
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2), 'utf-8');
  console.log('Done!');
}

main();
