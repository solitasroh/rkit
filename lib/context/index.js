/**
 * Context Module - Unified entry point
 * @module lib/context
 * @version 2.1.10
 *
 * Re-exports all context sub-modules for convenient access.
 * Each sub-module is independently usable via direct require.
 *
 * NOTE (bkit-gstack-sync-v2 / Cycle 1, C2):
 *   self-healing.js / ops-metrics.js / decision-record.js were removed
 *   in bkit v2.1.0 S1 dead code cleanup (commit 21d35d6). Their re-exports
 *   here are dropped — the facade now matches bkit upstream (5 files in
 *   lib/context/).
 */

const contextLoader = require('./context-loader');
const impactAnalyzer = require('./impact-analyzer');
const invariantChecker = require('./invariant-checker');
const scenarioRunner = require('./scenario-runner');

module.exports = {
  // context-loader
  loadPlanContext: contextLoader.loadPlanContext,
  loadDesignContext: contextLoader.loadDesignContext,
  extractContextAnchor: contextLoader.extractContextAnchor,
  injectAnchorToTemplate: contextLoader.injectAnchorToTemplate,

  // impact-analyzer
  analyzeImpact: impactAnalyzer.analyzeImpact,
  getMemoryImpact: impactAnalyzer.getMemoryImpact,
  getDtsImpact: impactAnalyzer.getDtsImpact,
  getDependencyImpact: impactAnalyzer.getDependencyImpact,

  // invariant-checker
  checkInvariants: invariantChecker.checkInvariants,

  // scenario-runner
  runScenario: scenarioRunner.runScenario,
  getScenarioCommands: scenarioRunner.getScenarioCommands,
};
