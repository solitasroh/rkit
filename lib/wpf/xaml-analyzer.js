/**
 * XAML Binding & Resource Analyzer
 * @module lib/wpf/xaml-analyzer
 * @version 0.4.0
 *
 * WPF binding patterns (verified):
 *   {Binding Path=PropertyName}           — standard
 *   {Binding PropertyName}                — Path omitted (default)
 *   {Binding Path=..., Mode=TwoWay}       — with mode
 *   {Binding ElementName=..., Path=...}   — element reference
 *   {Binding RelativeSource=...}          — relative source
 *   {TemplateBinding PropertyName}        — in ControlTemplate
 *   MultiBinding + IMultiValueConverter   — composite
 *
 *   {x:Bind} is UWP/WinUI ONLY → NOT supported in WPF
 *
 * Markup Extensions (separate from Binding):
 *   {StaticResource ResourceKey}
 *   {DynamicResource ResourceKey}
 *
 * Binding errors are RUNTIME ONLY (no compile-time detection)
 * Output pattern: "System.Windows.Data Error: 40"
 */

const fs = require('fs');
const path = require('path');

/**
 * Extract binding paths from XAML file
 * @param {string} xamlFilePath
 * @returns {Array<{path: string, mode: string|null, type: string, line: number}>}
 */
function extractBindings(xamlFilePath) {
  const content = fs.readFileSync(xamlFilePath, 'utf-8');
  const lines = content.split('\n');
  const bindings = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // {Binding Path=PropertyName} or {Binding PropertyName}
    const bindingRegex = /\{Binding\s+(?:Path=)?(\w[\w.]*?)(?:\s*,\s*Mode=(\w+))?\s*\}/g;
    let match;
    while ((match = bindingRegex.exec(line)) !== null) {
      bindings.push({
        path: match[1],
        mode: match[2] || null,
        type: 'Binding',
        line: i + 1,
      });
    }

    // {Binding ElementName=..., Path=...}
    const elemRegex = /\{Binding\s+ElementName=(\w+),\s*Path=(\w[\w.]*)/g;
    while ((match = elemRegex.exec(line)) !== null) {
      bindings.push({
        path: `${match[1]}.${match[2]}`,
        mode: null,
        type: 'ElementBinding',
        line: i + 1,
      });
    }

    // {TemplateBinding PropertyName}
    const templateRegex = /\{TemplateBinding\s+(\w[\w.]*)\}/g;
    while ((match = templateRegex.exec(line)) !== null) {
      bindings.push({
        path: match[1],
        mode: null,
        type: 'TemplateBinding',
        line: i + 1,
      });
    }
  }

  return bindings;
}

/**
 * Validate bindings against ViewModel properties
 * @param {Array} bindings - extractBindings result
 * @param {string} viewModelPath - ViewModel .cs file
 * @returns {{ matched: string[], unmatched: string[], extra: string[] }}
 */
function validateBindings(bindings, viewModelPath) {
  const vmContent = fs.readFileSync(viewModelPath, 'utf-8');
  const result = { matched: [], unmatched: [], extra: [] };

  // Extract public properties
  const propRegex = /public\s+\w[\w<>?,\s]*\s+(\w+)\s*\{/g;
  const vmProps = new Set();
  let match;
  while ((match = propRegex.exec(vmContent)) !== null) {
    vmProps.add(match[1]);
  }

  // Source Generator: [ObservableProperty] on private fields → PascalCase property
  const obsRegex = /\[ObservableProperty\]\s*(?:\[.*?\]\s*)*private\s+\w[\w<>?,\s]*\s+(\w+)\s*[;=]/g;
  while ((match = obsRegex.exec(vmContent)) !== null) {
    let fieldName = match[1];
    // Remove leading underscore and capitalize
    if (fieldName.startsWith('_')) fieldName = fieldName.substring(1);
    const propName = fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
    vmProps.add(propName);
  }

  // [RelayCommand] on methods → {MethodName}Command property
  const cmdRegex = /\[RelayCommand\]\s*(?:\[.*?\]\s*)*(?:private|public)\s+(?:async\s+)?(?:Task|void)\s+(\w+)\s*\(/g;
  while ((match = cmdRegex.exec(vmContent)) !== null) {
    vmProps.add(match[1] + 'Command');
  }

  // Compare bindings against VM properties
  const bindingPaths = new Set(bindings
    .filter(b => b.type === 'Binding')
    .map(b => b.path.split('.')[0]));

  for (const bp of bindingPaths) {
    if (vmProps.has(bp)) {
      result.matched.push(bp);
    } else {
      result.unmatched.push(bp);
    }
  }

  // Extra VM properties not bound
  for (const vp of vmProps) {
    if (!bindingPaths.has(vp) && !vp.endsWith('Command')) {
      result.extra.push(vp);
    }
  }

  return result;
}

/**
 * Validate StaticResource/DynamicResource references
 * @param {string} xamlFilePath
 * @param {string[]} resourceDictPaths
 * @returns {{ valid: boolean, missingResources: string[] }}
 */
function validateResources(xamlFilePath, resourceDictPaths) {
  const content = fs.readFileSync(xamlFilePath, 'utf-8');
  const missing = [];

  // Collect all defined resource keys from dictionaries
  const definedKeys = new Set();
  for (const rdPath of resourceDictPaths) {
    if (!fs.existsSync(rdPath)) continue;
    const rdContent = fs.readFileSync(rdPath, 'utf-8');
    const keyRegex = /x:Key="(\w+)"/g;
    let match;
    while ((match = keyRegex.exec(rdContent)) !== null) {
      definedKeys.add(match[1]);
    }
  }

  // Find referenced resources
  const refRegex = /\{(?:Static|Dynamic)Resource\s+(\w+)\}/g;
  let match;
  while ((match = refRegex.exec(content)) !== null) {
    const key = match[1];
    if (definedKeys.size > 0 && !definedKeys.has(key)) {
      missing.push(key);
    }
  }

  return { valid: missing.length === 0, missingResources: missing };
}

module.exports = { extractBindings, validateBindings, validateResources };
