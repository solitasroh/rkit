/**
 * Cross-Domain Utilities
 * @module lib/domain/cross
 * @version 0.1.0
 *
 * Handles MCU↔WPF serial communication validation
 * and cross-domain gap analysis.
 */

const fs = require('fs');
const path = require('path');

/**
 * Validate serial protocol consistency between MCU and WPF
 *
 * Checks that baud rate, data bits, parity, stop bits match
 * between MCU UART config and WPF SerialPort config.
 *
 * @param {string} mcuProtocolFile - MCU protocol definition file (.c/.h with UART config)
 * @param {string} wpfSerialFile - WPF SerialPort config file (.cs with SerialPort setup)
 * @returns {{ matched: boolean, mismatches: string[] }}
 */
function validateSerialProtocol(mcuProtocolFile, wpfSerialFile) {
  const mismatches = [];

  if (!mcuProtocolFile || !wpfSerialFile) {
    return { matched: true, mismatches: [] };
  }

  try {
    const mcuContent = fs.existsSync(mcuProtocolFile)
      ? fs.readFileSync(mcuProtocolFile, 'utf-8') : '';
    const wpfContent = fs.existsSync(wpfSerialFile)
      ? fs.readFileSync(wpfSerialFile, 'utf-8') : '';

    if (!mcuContent || !wpfContent) {
      return { matched: true, mismatches: [] };
    }

    // Extract baud rate from MCU (HAL_UART patterns)
    const mcuBaudMatch = mcuContent.match(/BaudRate\s*=\s*(\d+)/i)
      || mcuContent.match(/huart\d*\.Init\.BaudRate\s*=\s*(\d+)/);
    // Extract baud rate from WPF (SerialPort patterns)
    const wpfBaudMatch = wpfContent.match(/BaudRate\s*=\s*(\d+)/)
      || wpfContent.match(/new\s+SerialPort\s*\([^,]*,\s*(\d+)/);

    if (mcuBaudMatch && wpfBaudMatch) {
      if (mcuBaudMatch[1] !== wpfBaudMatch[1]) {
        mismatches.push(
          `BaudRate mismatch: MCU=${mcuBaudMatch[1]}, WPF=${wpfBaudMatch[1]}`
        );
      }
    }

    // Extract word length from MCU
    const mcuWordMatch = mcuContent.match(/WordLength\s*=\s*UART_WORDLENGTH_(\d+)/i);
    const wpfDataMatch = wpfContent.match(/DataBits\s*=\s*(\d+)/);
    if (mcuWordMatch && wpfDataMatch) {
      const mcuBits = mcuWordMatch[1].replace('B', '');
      if (mcuBits !== wpfDataMatch[1]) {
        mismatches.push(
          `DataBits mismatch: MCU=${mcuBits}, WPF=${wpfDataMatch[1]}`
        );
      }
    }

    // Extract parity
    const mcuParityMatch = mcuContent.match(/Parity\s*=\s*UART_PARITY_(\w+)/i);
    const wpfParityMatch = wpfContent.match(/Parity\s*=\s*Parity\.(\w+)/);
    if (mcuParityMatch && wpfParityMatch) {
      if (mcuParityMatch[1].toLowerCase() !== wpfParityMatch[1].toLowerCase()) {
        mismatches.push(
          `Parity mismatch: MCU=${mcuParityMatch[1]}, WPF=${wpfParityMatch[1]}`
        );
      }
    }

    // Extract stop bits
    const mcuStopMatch = mcuContent.match(/StopBits\s*=\s*UART_STOPBITS_(\w+)/i);
    const wpfStopMatch = wpfContent.match(/StopBits\s*=\s*StopBits\.(\w+)/);
    if (mcuStopMatch && wpfStopMatch) {
      // Normalize: MCU "1" / "2" / "0_5" → WPF "One" / "Two" / "OnePointFive"
      const stopNormMap = { '1': 'one', '2': 'two', '0_5': 'onepointfive', '1_5': 'onepointfive' };
      const mcuNorm = (stopNormMap[mcuStopMatch[1]] || mcuStopMatch[1]).toLowerCase();
      const wpfNorm = wpfStopMatch[1].toLowerCase();
      if (mcuNorm !== wpfNorm) {
        mismatches.push(
          `StopBits mismatch: MCU=${mcuStopMatch[1]}, WPF=${wpfStopMatch[1]}`
        );
      }
    }
  } catch (e) {
    // Non-critical - return matched if can't parse
    return { matched: true, mismatches: [] };
  }

  return { matched: mismatches.length === 0, mismatches };
}

/**
 * Generate cross-domain gap analysis items
 * Checks if MCU and WPF projects in the same repo have matching serial configs
 *
 * @returns {Array<{source: string, target: string, item: string, status: string}>}
 */
function generateCrossDomainGapItems() {
  const items = [];

  try {
    const detector = require('./detector');
    const info = detector.getCachedDomainInfo();

    if (!info || !info.secondary) {
      return items;
    }

    // Only relevant for MCU+WPF cross-domain projects
    if (
      (info.domain === 'mcu' && info.secondary === 'wpf') ||
      (info.domain === 'wpf' && info.secondary === 'mcu')
    ) {
      items.push({
        source: 'MCU (UART config)',
        target: 'WPF (SerialPort config)',
        item: 'Serial communication parameters (baud, parity, stop bits)',
        status: 'needs-verification',
      });
      items.push({
        source: 'MCU (protocol definition)',
        target: 'WPF (protocol parser)',
        item: 'Message framing / packet structure consistency',
        status: 'needs-verification',
      });
    }
  } catch (_) {}

  return items;
}

/**
 * Detect if current project is a cross-domain project
 * @returns {{ isCrossDomain: boolean, primary: string|null, secondary: string|null }}
 */
function detectCrossDomain() {
  try {
    const detector = require('./detector');
    const info = detector.getCachedDomainInfo();
    return {
      isCrossDomain: !!(info && info.secondary),
      primary: info ? info.domain : null,
      secondary: info ? info.secondary : null,
    };
  } catch (_) {
    return { isCrossDomain: false, primary: null, secondary: null };
  }
}

module.exports = {
  validateSerialProtocol,
  generateCrossDomainGapItems,
  detectCrossDomain,
};
