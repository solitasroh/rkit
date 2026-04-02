/**
 * lib/ui — Workflow Visualization UX Public API
 * @module lib/ui
 * @version 3.0.0
 *
 * Dual-render UI components: terminal (ANSI/stderr) + context (markdown/LLM).
 * Each component exports { terminal(), context() } + backward-compatible renderXxx().
 */

// Engines
const terminal = require('./engines/terminal');
const markdown = require('./engines/markdown');

// Components (dual render)
const progressBar = require('./components/progress-bar');
const workflowMap = require('./components/workflow-map');
const controlPanel = require('./components/control-panel');
const agentPanel = require('./components/agent-panel');
const impactView = require('./components/impact-view');
const budgetGauge = require('./components/budget-gauge');
const sparkline = require('./components/sparkline');

// Config
const { loadUiConfig, getThreshold, getBarWidth } = require('./config-loader');

module.exports = {
  // Engines (new API)
  terminal,
  markdown,

  // Components (new API — each has .terminal() and .context())
  progressBar,
  workflowMap,
  controlPanel,
  agentPanel,
  impactView,
  budgetGauge,
  sparkline,

  // Config
  loadUiConfig,
  getThreshold,
  getBarWidth,

  // Backward-compatible API (calls terminal() internally)
  renderPdcaProgressBar: progressBar.renderPdcaProgressBar,
  renderWorkflowMap: workflowMap.renderWorkflowMap,
  renderControlPanel: controlPanel.renderControlPanel,
  renderAgentPanel: agentPanel.renderAgentPanel,
  renderImpactView: impactView.renderImpactView,

  // ANSI utilities (backward-compatible, from ansi.js)
  ...require('./ansi'),
};
