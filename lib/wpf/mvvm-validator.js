/**
 * MVVM Pattern Validator
 * @module lib/wpf/mvvm-validator
 * @version 0.4.0
 *
 * MVVM framework priority (verified):
 *   1. CommunityToolkit.Mvvm (free, recommended)
 *   2. Prism (v9.0+ commercial license, caution for new projects)
 *   3. Direct INotifyPropertyChanged (small projects)
 *
 * Source Generator awareness:
 *   [ObservableProperty] on private field → auto-generates property
 *   [RelayCommand] on method → auto-generates ICommand property
 */

const fs = require('fs');

/**
 * Validate ViewModel follows MVVM pattern
 * @param {string} viewModelPath
 * @returns {{ score: number, issues: string[] }}
 */
function validateViewModel(viewModelPath) {
  const content = fs.readFileSync(viewModelPath, 'utf-8');
  const issues = [];
  let score = 100;

  // Check 1: Inherits from MVVM base class
  const hasObservableObject = content.includes('ObservableObject') ||
    content.includes('BindableBase') ||
    content.includes('INotifyPropertyChanged');
  const hasObservableProp = content.includes('[ObservableProperty]');

  if (!hasObservableObject && !hasObservableProp) {
    issues.push('ViewModel does not implement INotifyPropertyChanged or inherit ObservableObject');
    score -= 30;
  }

  // Check 2: Uses ICommand pattern
  const hasCommand = content.includes('RelayCommand') ||
    content.includes('DelegateCommand') ||
    content.includes('ICommand') ||
    content.includes('[RelayCommand]');

  if (!hasCommand && content.includes('Click') && !content.includes('// ')) {
    issues.push('Consider using ICommand/RelayCommand instead of Click event handlers');
    score -= 10;
  }

  // Check 3: No direct View references (System.Windows.Controls, etc.)
  const viewNamespaces = [
    'System.Windows.Controls',
    'System.Windows.Media',
    'System.Windows.Shapes',
    'System.Windows.Documents',
  ];
  // System.Windows.Input.ICommand is allowed
  for (const ns of viewNamespaces) {
    if (content.includes(`using ${ns}`) || content.includes(`${ns}.`)) {
      issues.push(`ViewModel references UI namespace: ${ns} (violates MVVM separation)`);
      score -= 20;
    }
  }

  // Check 4: Constructor DI pattern
  const ctorRegex = /public\s+\w+ViewModel\s*\(([^)]+)\)/;
  const ctorMatch = content.match(ctorRegex);
  if (ctorMatch && ctorMatch[1].includes('I')) {
    // Has constructor with interface parameters → good DI pattern
  } else if (content.includes('new ') && content.includes('Service')) {
    issues.push('Consider using constructor DI instead of direct instantiation (new XxxService)');
    score -= 10;
  }

  return { score: Math.max(0, score), issues };
}

/**
 * Analyze .csproj for WPF project info
 * @param {string} csprojPath
 * @returns {{ framework: string, isWpf: boolean, isNetFramework: boolean, packages: Array, warnings: string[] }}
 */
function analyzeCsproj(csprojPath) {
  const content = fs.readFileSync(csprojPath, 'utf-8');
  const result = {
    framework: 'unknown',
    isWpf: false,
    isNetFramework: false,
    packages: [],
    warnings: [],
  };

  // .NET 8+ SDK-style
  const tfmMatch = content.match(/<TargetFramework>([\w.-]+)<\/TargetFramework>/);
  if (tfmMatch) {
    result.framework = tfmMatch[1];
    if (!tfmMatch[1].includes('-windows') && content.includes('<UseWPF>')) {
      result.warnings.push(`TargetFramework "${tfmMatch[1]}" missing -windows suffix (should be net8.0-windows)`);
    }
  }

  // .NET Framework
  const fwMatch = content.match(/<TargetFrameworkVersion>v([\d.]+)<\/TargetFrameworkVersion>/);
  if (fwMatch) {
    result.framework = `.NET Framework ${fwMatch[1]}`;
    result.isNetFramework = true;
  }

  // WPF detection
  result.isWpf = content.includes('<UseWPF>true</UseWPF>') ||
    content.includes('<UseWPF>True</UseWPF>') ||
    content.includes('PresentationFramework');

  // NuGet packages
  const pkgRegex = /<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]+)")?/g;
  let match;
  while ((match = pkgRegex.exec(content)) !== null) {
    result.packages.push({ name: match[1], version: match[2] || 'unknown' });
  }

  // Warnings
  if (result.isWpf && !result.packages.some(p => p.name === 'CommunityToolkit.Mvvm')) {
    result.warnings.push('CommunityToolkit.Mvvm not found. Recommended for MVVM pattern.');
  }

  if (result.packages.some(p => p.name.startsWith('Prism'))) {
    result.warnings.push('Prism detected. Note: Prism 9.0+ requires commercial license.');
  }

  // SerialPort check
  if (!result.isNetFramework && !result.packages.some(p => p.name === 'System.IO.Ports')) {
    // Only warn if serial-related code exists (check later)
  }

  return result;
}

module.exports = { validateViewModel, analyzeCsproj };
