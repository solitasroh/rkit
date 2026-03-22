/**
 * Linux Kernel Config Parser
 * @module lib/mpu/kernel-config
 * @version 0.3.0
 */

const fs = require('fs');

/**
 * Parse kernel .config file
 * @param {string} configPath
 * @returns {Map<string, string>} CONFIG_KEY → value (y/m/n/string)
 */
function parseKernelConfig(configPath) {
  const content = fs.readFileSync(configPath, 'utf-8');
  const config = new Map();

  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const match = trimmed.match(/^(CONFIG_\w+)=(.+)$/);
    if (match) {
      config.set(match[1], match[2].replace(/^"|"$/g, ''));
    }
  }

  return config;
}

/**
 * Get enabled kernel modules (CONFIG_*=m)
 * @param {Map} configMap
 * @returns {string[]}
 */
function getEnabledModules(configMap) {
  return [...configMap.entries()]
    .filter(([, v]) => v === 'm')
    .map(([k]) => k.replace('CONFIG_', ''));
}

/**
 * Get built-in drivers (CONFIG_*=y)
 * @param {Map} configMap
 * @returns {string[]}
 */
function getEnabledDrivers(configMap) {
  return [...configMap.entries()]
    .filter(([k, v]) => v === 'y' && k.includes('_DRV') || k.includes('_DRIVER'))
    .map(([k]) => k.replace('CONFIG_', ''));
}

module.exports = { parseKernelConfig, getEnabledModules, getEnabledDrivers };
