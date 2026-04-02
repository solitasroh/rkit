/**
 * Impact Analysis View — Dual-Render Component
 * @module lib/ui/components/impact-view
 *
 * terminal(data, config) -> ANSI string (stderr)
 * context(data, config)  -> markdown string (additionalContext)
 * renderImpactView()     -> backward-compatible wrapper
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');
const sparkline = require('./sparkline');

// ============================================================
// Constants
// ============================================================

const TREE_BRANCH  = '\u251C\u2500\u2500 ';  // +--
const TREE_LAST    = '\u2514\u2500\u2500 ';  // L--
const TREE_PIPE    = '\u2502   ';             // |
const TREE_SPACE   = '    ';

// ============================================================
// Internal Helpers
// ============================================================

function resolveFeature(pdcaStatus, featureName) {
  if (!pdcaStatus) return { name: null, data: null };
  const features = pdcaStatus.features || {};
  if (featureName && features[featureName]) {
    return { name: featureName, data: features[featureName] };
  }
  const primary = pdcaStatus.primaryFeature || pdcaStatus.activeFeature;
  if (primary && features[primary]) {
    return { name: primary, data: features[primary] };
  }
  const keys = Object.keys(features);
  if (keys.length === 1) {
    return { name: keys[0], data: features[keys[0]] };
  }
  return { name: featureName || null, data: null };
}

function buildFileTree(files, maxDepth, maxFiles) {
  if (!files || files.length === 0) return ['(no changed files)'];

  // Find common prefix
  const parts = files.map(f => f.replace(/\\/g, '/').split('/'));
  let prefix = [];
  if (parts.length > 1) {
    outer:
    for (let i = 0; i < parts[0].length; i++) {
      const seg = parts[0][i];
      for (let j = 1; j < parts.length; j++) {
        if (!parts[j][i] || parts[j][i] !== seg) break outer;
      }
      prefix.push(seg);
    }
  }

  // Build tree structure
  const tree = {};
  const displayed = files.slice(0, maxFiles);
  const remaining = files.length - displayed.length;

  for (const file of displayed) {
    const rel = file.replace(/\\/g, '/').split('/').slice(prefix.length);
    const truncatedPath = rel.length > maxDepth
      ? [...rel.slice(0, maxDepth - 1), rel.slice(maxDepth - 1).join('/')]
      : rel;

    let node = tree;
    for (let i = 0; i < truncatedPath.length; i++) {
      const seg = truncatedPath[i];
      if (i === truncatedPath.length - 1) {
        node[seg] = null;
      } else {
        if (!node[seg] || typeof node[seg] !== 'object') {
          node[seg] = {};
        }
        node = node[seg];
      }
    }
  }

  // Render tree recursively
  const lines = [];
  function renderNode(obj, indent) {
    if (!obj || typeof obj !== 'object') return;
    const keys = Object.keys(obj).sort((a, b) => {
      const aIsDir = obj[a] !== null;
      const bIsDir = obj[b] !== null;
      if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
      return a.localeCompare(b);
    });

    for (let i = 0; i < keys.length; i++) {
      const isLast = i === keys.length - 1;
      const branch = isLast ? TREE_LAST : TREE_BRANCH;
      const childIndent = indent + (isLast ? TREE_SPACE : TREE_PIPE);
      const key = keys[i];

      if (obj[key] !== null && typeof obj[key] === 'object') {
        lines.push(`${indent}${branch}${key}/`);
        renderNode(obj[key], childIndent);
      } else {
        lines.push(`${indent}${branch}${key}`);
      }
    }
  }

  if (prefix.length > 0) {
    lines.push(prefix.join('/') + '/');
  }
  renderNode(tree, prefix.length > 0 ? '  ' : '');

  if (remaining > 0) {
    lines.push(T.dim(`  \u2026 ${remaining} more files`));
  }

  return lines;
}

// ============================================================
// Dual-Render API
// ============================================================

/**
 * Terminal render — ANSI match rate bar + file tree + sparkline trend.
 * @param {Object} data - { pdcaStatus, gitDiff, feature }
 * @param {Object} [config] - { maxFiles, treeDepth, width }
 * @returns {string}
 */
function terminal(data, config = {}) {
  const uiConfig = loadUiConfig();
  const width = config.width || T.getTermWidth();
  const bp = T.getWidthBreakpoint();
  const maxFiles = config.maxFiles != null ? config.maxFiles : uiConfig.layout.maxTreeFiles;
  const treeDepth = config.treeDepth != null ? config.treeDepth : uiConfig.layout.maxTreeDepth;
  const innerWidth = width - 6;
  const thresholds = uiConfig.thresholds.matchRate;

  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);
  const gitDiff = data.gitDiff;

  const lines = [];

  // Title
  const titleText = featureName
    ? ` Impact Analysis: ${T.truncate(featureName, 30)} `
    : ' Impact Analysis ';
  const titlePad = Math.max(1, width - titleText.length - 5);
  lines.push(`${T.BOX.topLeft}${T.hline(3)}${titleText}${T.hline(titlePad)}${T.BOX.topRight}`);

  lines.push(T.boxLine('', innerWidth));

  // Match Rate bar
  const matchRate = featureData && featureData.matchRate != null
    ? featureData.matchRate
    : null;

  if (matchRate != null) {
    const barWidth = uiConfig.layout.barWidths[bp] || uiConfig.layout.barWidths.normal;
    const color = T.rateColor(matchRate, thresholds);
    const bar = T.progressBar(matchRate, barWidth, color);
    const rateStr = `${matchRate}%`;
    const target = `(target: ${thresholds.good}%)`;
    const rateLine = `Match Rate  ${bar}  ${T.bold(rateStr)}  ${T.dim(target)}`;
    lines.push(T.boxLine(rateLine, innerWidth));
  } else {
    lines.push(T.boxLine(T.dim('Match Rate: N/A'), innerWidth));
  }

  lines.push(T.boxLine('', innerWidth));

  // Changed files section
  const changedFiles = (gitDiff && gitDiff.changedFiles) || [];
  const stats = (gitDiff && gitDiff.stats) || {};
  const insertions = stats.insertions || 0;
  const deletions = stats.deletions || 0;
  const filesChanged = stats.filesChanged || changedFiles.length;

  const filesHeader = `Changed Files (${filesChanged} files, ${T.colorize(`+${insertions}`, 'green')} / ${T.colorize(`-${deletions}`, 'red')})`;
  lines.push(T.boxLine(filesHeader, innerWidth));

  const treeLines = buildFileTree(changedFiles, treeDepth, maxFiles);
  for (const treeLine of treeLines) {
    lines.push(T.boxLine(T.truncate(treeLine, innerWidth), innerWidth));
  }

  lines.push(T.boxLine('', innerWidth));

  // Iteration match rate trend with sparkline
  const iterHistory = featureData && featureData.iterationHistory;
  if (iterHistory && iterHistory.length > 0) {
    const trendHeader = `${T.hline(3)} Iteration Match Rate Trend ${T.hline(Math.max(1, innerWidth - 35))}`;
    lines.push(T.boxLine(trendHeader, innerWidth));

    // Per-iteration bars
    const trendBarWidth = Math.min(20, uiConfig.layout.barWidths[bp] || 20);
    for (const iter of iterHistory) {
      const iterNum = iter.iteration || '?';
      const rate = iter.matchRate != null ? iter.matchRate : 0;
      const isCurrent = !iter.completedAt;
      const color = T.rateColor(rate, thresholds);
      const bar = T.progressBar(rate, trendBarWidth, color);
      const label = `Iter ${String(iterNum).padStart(2)}`;
      const rateStr = `${rate}%`;
      const currentTag = isCurrent ? T.bold(' (current)') : '';

      lines.push(T.boxLine(`${label} ${bar}  ${rateStr}${currentTag}`, innerWidth));
    }

    // Sparkline summary
    const trendValues = iterHistory
      .filter(i => i.matchRate != null)
      .map(i => i.matchRate);
    if (trendValues.length > 1) {
      const sparklineStr = sparkline.terminal(trendValues, { label: 'Trend' });
      lines.push(T.boxLine('', innerWidth));
      lines.push(T.boxLine(sparklineStr, innerWidth));
    }

    lines.push(T.boxLine('', innerWidth));
  }

  // Close box
  lines.push(`${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`);

  return lines.join('\n');
}

/**
 * Context render — compact impact summary text.
 * @param {Object} data - { pdcaStatus, gitDiff, feature }
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config = {}) {
  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);
  const gitDiff = data.gitDiff;

  const matchRate = featureData && featureData.matchRate != null
    ? featureData.matchRate
    : null;

  const changedFiles = (gitDiff && gitDiff.changedFiles) || [];
  const stats = (gitDiff && gitDiff.stats) || {};
  const insertions = stats.insertions || 0;
  const deletions = stats.deletions || 0;
  const filesChanged = stats.filesChanged || changedFiles.length;

  const rateStr = matchRate != null ? `${matchRate}%` : 'N/A';
  const parts = [`Match Rate: ${rateStr}`];
  parts.push(`Changed: ${filesChanged} files (+${insertions}, -${deletions})`);

  // Sparkline trend if available
  const iterHistory = featureData && featureData.iterationHistory;
  if (iterHistory && iterHistory.length > 1) {
    const trendValues = iterHistory
      .filter(i => i.matchRate != null)
      .map(i => i.matchRate);
    if (trendValues.length > 1) {
      parts.push(sparkline.context(trendValues, { label: 'Trend' }));
    }
  }

  return parts.join(', ');
}

/**
 * Backward-compatible wrapper.
 * @param {Object|null} pdcaStatus
 * @param {Object|null} gitDiff
 * @param {Object} [opts]
 * @returns {string}
 */
function renderImpactView(pdcaStatus, gitDiff, opts = {}) {
  return terminal(
    { pdcaStatus, gitDiff, feature: opts.feature },
    { maxFiles: opts.maxFiles, treeDepth: opts.treeDepth, width: opts.width }
  );
}

module.exports = { terminal, context, renderImpactView };
