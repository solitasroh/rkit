/**
 * Embedded Threat Model — STRIDE-based threat catalog for MCU/MPU/WPF
 * @module lib/quality/embedded-threat-model
 * @version 1.0.0
 *
 * Provides domain-specific threat catalogs, confidence-based filtering,
 * and false-positive exclusion rules for embedded security review.
 */

/**
 * @typedef {Object} Threat
 * @property {string} id - Threat identifier
 * @property {string} stride - STRIDE category
 * @property {string} domain - 'mcu'|'mpu'|'wpf'|'all'
 * @property {string} title - Threat title
 * @property {string} description - Detailed description
 * @property {string} severity - 'critical'|'high'|'medium'|'low'
 * @property {RegExp|null} pattern - Detection pattern (null = manual review)
 * @property {string[]} mitigations - Recommended mitigations
 */

/**
 * STRIDE threat catalog for embedded systems
 * @type {Threat[]}
 */
const THREAT_CATALOG = [
  // === SPOOFING ===
  {
    id: 'S-MCU-001', stride: 'Spoofing', domain: 'mcu',
    title: 'Firmware update forgery',
    description: 'Unsigned or weakly signed firmware updates can be replaced with malicious firmware.',
    severity: 'critical',
    pattern: /\b(firmware_update|fwupdate|ota_update)\b/i,
    mitigations: ['Implement secure boot chain', 'Sign firmware with asymmetric keys', 'Verify signature before flash write'],
  },
  {
    id: 'S-MCU-002', stride: 'Spoofing', domain: 'mcu',
    title: 'Bootloader tampering',
    description: 'Unprotected bootloader can be modified to bypass security checks.',
    severity: 'critical',
    pattern: /\b(bootloader|boot_config|BOOT_ADDRESS)\b/i,
    mitigations: ['Write-protect bootloader flash region', 'Implement boot integrity check'],
  },
  {
    id: 'S-MPU-001', stride: 'Spoofing', domain: 'mpu',
    title: 'Kernel module impersonation',
    description: 'Unsigned kernel modules can be loaded, impersonating legitimate drivers.',
    severity: 'high',
    pattern: /\b(insmod|modprobe|MODULE_LICENSE)\b/i,
    mitigations: ['Enable CONFIG_MODULE_SIG', 'Require module signing'],
  },
  {
    id: 'S-MPU-002', stride: 'Spoofing', domain: 'mpu',
    title: 'Shared library replacement (LD_PRELOAD)',
    description: 'LD_PRELOAD can inject malicious shared libraries, replacing legitimate ones.',
    severity: 'high',
    pattern: /\b(LD_PRELOAD|dlopen|dlsym)\b/i,
    mitigations: ['Set SUID bit carefully', 'Use full paths in library loading', 'Disable LD_PRELOAD for privileged binaries'],
  },
  {
    id: 'S-WPF-001', stride: 'Spoofing', domain: 'wpf',
    title: 'DLL injection',
    description: 'Malicious DLLs can be loaded into the application process.',
    severity: 'high',
    pattern: /\b(LoadLibrary|DllImport|P\/Invoke)\b/i,
    mitigations: ['Use DLL search order hardening', 'Sign all assemblies', 'Validate loaded assembly identity'],
  },

  // === TAMPERING ===
  {
    id: 'T-MCU-001', stride: 'Tampering', domain: 'mcu',
    title: 'Flash direct modification',
    description: 'Flash memory can be modified via debug interface or during update.',
    severity: 'high',
    pattern: /\b(FLASH_Program|HAL_FLASH_Program|flash_write|flash_erase)\b/i,
    mitigations: ['Enable read-out protection (RDP)', 'Implement flash integrity checks (CRC/hash)'],
  },
  {
    id: 'T-MPU-001', stride: 'Tampering', domain: 'mpu',
    title: 'Device Tree overlay tampering',
    description: 'DT overlays can modify hardware configuration at runtime.',
    severity: 'medium',
    pattern: /\b(dtoverlay|configfs.*dtbo|of_overlay)\b/i,
    mitigations: ['Restrict DT overlay application to privileged users', 'Verify overlay signatures'],
  },
  {
    id: 'T-WPF-001', stride: 'Tampering', domain: 'wpf',
    title: 'Configuration file modification',
    description: 'Application config files can be modified to change behavior.',
    severity: 'medium',
    pattern: /\b(app\.config|appsettings\.json|\.config)\b/i,
    mitigations: ['Encrypt sensitive config values', 'Verify config file integrity at startup'],
  },

  // === INFORMATION DISCLOSURE ===
  {
    id: 'I-MCU-001', stride: 'Information Disclosure', domain: 'mcu',
    title: 'JTAG/SWD debug port open',
    description: 'Open debug ports allow full memory access and firmware extraction.',
    severity: 'critical',
    pattern: /\b(JTAG|SWD|SWDIO|SWCLK|openocd)\b/i,
    mitigations: ['Disable JTAG/SWD in production (fuse bits)', 'Enable read-out protection'],
  },
  {
    id: 'I-MCU-002', stride: 'Information Disclosure', domain: 'mcu',
    title: 'UART debug output in production',
    description: 'Debug prints via UART can expose internal state and secrets.',
    severity: 'high',
    pattern: /\b(printf|UART_Transmit|HAL_UART_Transmit|debug_print)\b/i,
    mitigations: ['Compile out debug prints in release builds (#ifdef DEBUG)', 'Use conditional compilation'],
  },
  {
    id: 'I-MPU-001', stride: 'Information Disclosure', domain: 'mpu',
    title: '/proc information exposure',
    description: '/proc filesystem can expose sensitive kernel and process information.',
    severity: 'medium',
    pattern: /\b(\/proc\/|procfs|seq_file|proc_create)\b/i,
    mitigations: ['Restrict /proc access with hidepid mount option', 'Limit debugfs exposure'],
  },
  {
    id: 'I-WPF-001', stride: 'Information Disclosure', domain: 'wpf',
    title: 'Serial port data sniffing',
    description: 'Unencrypted serial communication can be intercepted.',
    severity: 'medium',
    pattern: /\b(SerialPort|COM\d|BaudRate)\b/i,
    mitigations: ['Encrypt serial payload if sensitive', 'Implement message authentication'],
  },

  // === DENIAL OF SERVICE ===
  {
    id: 'D-MCU-001', stride: 'DoS', domain: 'mcu',
    title: 'Interrupt storm',
    description: 'Rapidly triggering interrupts can prevent normal operation.',
    severity: 'high',
    pattern: /\b(HAL_GPIO_EXTI_Callback|EXTI_IRQHandler|NVIC_EnableIRQ)\b/i,
    mitigations: ['Implement interrupt rate limiting', 'Use debouncing for external interrupts'],
  },
  {
    id: 'D-MPU-001', stride: 'DoS', domain: 'mpu',
    title: 'OOM killer trigger',
    description: 'Uncontrolled memory allocation can trigger OOM killer.',
    severity: 'high',
    pattern: /\b(malloc|kmalloc|vmalloc|kzalloc)\b/i,
    mitigations: ['Set memory limits (cgroups)', 'Implement allocation size checks', 'Use memory pools'],
  },
  {
    id: 'D-WPF-001', stride: 'DoS', domain: 'wpf',
    title: 'UI thread blocking',
    description: 'Long-running operations on UI thread freeze the application.',
    severity: 'medium',
    pattern: /\b(Thread\.Sleep|\.Result\b|\.Wait\(\)|\.GetAwaiter\(\)\.GetResult\(\))\b/i,
    mitigations: ['Use async/await pattern', 'Move heavy work to background threads', 'Use Task.Run for CPU-bound work'],
  },

  // === ELEVATION OF PRIVILEGE ===
  {
    id: 'E-MCU-001', stride: 'EoP', domain: 'mcu',
    title: 'Stack overflow',
    description: 'Buffer overflow on stack can overwrite return address.',
    severity: 'critical',
    pattern: /\b(char\s+\w+\[|sprintf|strcpy|strcat|gets)\b/i,
    mitigations: ['Use bounded string functions (snprintf, strncpy)', 'Enable stack canaries', 'Configure MPU stack guard'],
  },
  {
    id: 'E-MPU-001', stride: 'EoP', domain: 'mpu',
    title: 'setuid misuse',
    description: 'Improperly configured setuid binaries can be exploited.',
    severity: 'high',
    pattern: /\b(setuid|setgid|seteuid|cap_set_proc)\b/i,
    mitigations: ['Minimize setuid usage', 'Use Linux capabilities instead', 'Drop privileges immediately after use'],
  },
  {
    id: 'E-WPF-001', stride: 'EoP', domain: 'wpf',
    title: 'UAC bypass attempt',
    description: 'Application may attempt to bypass User Account Control.',
    severity: 'high',
    pattern: /\b(requireAdministrator|highestAvailable|runas|ShellExecute.*runas)\b/i,
    mitigations: ['Request minimum required privileges', 'Use manifest for privilege declaration'],
  },
];

/**
 * False-positive exclusion patterns
 * @type {Array<{pattern: RegExp, reason: string}>}
 */
const FALSE_POSITIVE_EXCLUSIONS = [
  { pattern: /\btest[s_-]?\//i, reason: 'Test directory — test credentials expected' },
  { pattern: /\bmock[s_-]?\//i, reason: 'Mock directory — mock values expected' },
  { pattern: /\bexample[s_-]?\//i, reason: 'Example directory — example values expected' },
  { pattern: /\.test\.(c|h|js|cs|xaml)$/i, reason: 'Test file' },
  { pattern: /\.spec\.(c|h|js|cs)$/i, reason: 'Spec file' },
  { pattern: /\bDEBUG\b.*\bprintf\b/i, reason: 'Debug-only print (conditional compilation)' },
];

/**
 * Analyze code for embedded security threats
 * @param {string} code - Code content to analyze
 * @param {string} filePath - File path for context
 * @param {string} domain - 'mcu'|'mpu'|'wpf'
 * @param {number} [minConfidence=8] - Minimum confidence threshold (0-10)
 * @returns {Array<{threat: Threat, confidence: number, location: string}>}
 */
function analyze(code, filePath, domain, minConfidence = 8) {
  const results = [];

  // Check false-positive exclusions
  const isExcluded = FALSE_POSITIVE_EXCLUSIONS.some(fp => fp.pattern.test(filePath));

  const applicableThreats = THREAT_CATALOG.filter(
    t => t.domain === domain || t.domain === 'all'
  );

  for (const threat of applicableThreats) {
    if (!threat.pattern) continue;

    const match = threat.pattern.test(code);
    if (!match) continue;

    // Calculate confidence based on context
    let confidence = 7; // Base confidence for pattern match

    // Boost confidence for critical severity
    if (threat.severity === 'critical') confidence += 1;

    // Reduce confidence for excluded paths
    if (isExcluded) confidence -= 3;

    // Boost for production-related paths
    if (/\b(src|lib|app|driver|core)\b/i.test(filePath)) confidence += 1;

    // Cap at 10
    confidence = Math.min(10, Math.max(0, confidence));

    if (confidence >= minConfidence) {
      results.push({
        threat: {
          id: threat.id,
          stride: threat.stride,
          title: threat.title,
          description: threat.description,
          severity: threat.severity,
          mitigations: threat.mitigations,
        },
        confidence,
        location: filePath,
      });
    }
  }

  return results;
}

/**
 * Get STRIDE summary for a domain
 * @param {string} domain - 'mcu'|'mpu'|'wpf'
 * @returns {Object<string, Threat[]>}
 */
function getStrideSummary(domain) {
  const summary = {};
  const categories = ['Spoofing', 'Tampering', 'Repudiation', 'Information Disclosure', 'DoS', 'EoP'];

  for (const cat of categories) {
    summary[cat] = THREAT_CATALOG.filter(
      t => t.stride === cat && (t.domain === domain || t.domain === 'all')
    );
  }

  return summary;
}

/**
 * Get all threats for a domain
 * @param {string} domain - 'mcu'|'mpu'|'wpf'
 * @returns {Threat[]}
 */
function getThreatsForDomain(domain) {
  return THREAT_CATALOG.filter(t => t.domain === domain || t.domain === 'all');
}

module.exports = {
  THREAT_CATALOG,
  FALSE_POSITIVE_EXCLUSIONS,
  analyze,
  getStrideSummary,
  getThreatsForDomain,
};
