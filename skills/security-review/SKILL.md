---
name: security-review
classification: capability
classification-reason: Security analysis capability independent of model advancement
deprecation-risk: none
description: |
  Full STRIDE threat modeling adapted for embedded systems (MCU/MPU/WPF).
  Domain-specific hardware threat vectors, confidence-based filtering, false-positive exclusion.
  Inspired by gstack /cso with embedded adaptation.

  Triggers: security review, STRIDE, threat model, 보안 리뷰, 위협 모델링,
  セキュリティレビュー, 脅威モデリング, 安全审查, 威胁建模,
  revisión de seguridad, revue de sécurité, Sicherheitsüberprüfung, revisione sicurezza

  Do NOT use for: general code review (use /code-review),
  OWASP web-only checks (use security-architect agent directly).
argument-hint: "[feature] [--domain mcu|mpu|wpf] [--confidence 8]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
imports: []
next-skill: null
pdca-phase: check
task-template: "[Security] {feature}"
---

# Security Review Skill

> STRIDE threat modeling for embedded systems. Confidence-gated, domain-specific.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `{feature}` | Feature to review | `/security-review uart-dma` |
| `--domain` | Force domain (auto-detected if omitted) | `--domain mcu` |
| `--confidence` | Minimum confidence 0-10 (default: 8) | `--confidence 7` |

## How It Works

1. Auto-detect domain (MCU/MPU/WPF) from project files
2. Scan implementation files for the feature
3. Run STRIDE threat analysis using `lib/quality/embedded-threat-model.js`
4. Filter results by confidence threshold (default >= 8/10)
5. Exclude false positives (test files, mocks, examples)
6. Generate security review report

## STRIDE Threat Matrix

### MCU Threats

| STRIDE | Threat | Severity | Detection |
|--------|--------|----------|-----------|
| Spoofing | Firmware update forgery | Critical | Pattern: firmware_update, ota_update |
| Spoofing | Bootloader tampering | Critical | Pattern: bootloader, BOOT_ADDRESS |
| Tampering | Flash direct modification | High | Pattern: FLASH_Program, flash_write |
| Info Disclosure | JTAG/SWD port open | Critical | Pattern: JTAG, SWD, openocd |
| Info Disclosure | UART debug in production | High | Pattern: printf, UART_Transmit |
| DoS | Interrupt storm | High | Pattern: EXTI_Callback, NVIC_EnableIRQ |
| EoP | Stack overflow | Critical | Pattern: sprintf, strcpy, gets |

### MPU Threats (Kernel/Driver/App)

| STRIDE | Threat | Severity | Detection |
|--------|--------|----------|-----------|
| Spoofing | Kernel module impersonation | High | Pattern: insmod, modprobe |
| Spoofing | Shared library replacement | High | Pattern: LD_PRELOAD, dlopen |
| Tampering | DT overlay tampering | Medium | Pattern: dtoverlay, of_overlay |
| Info Disclosure | /proc exposure | Medium | Pattern: /proc/, proc_create |
| DoS | OOM killer trigger | High | Pattern: malloc, kmalloc |
| EoP | setuid misuse | High | Pattern: setuid, cap_set_proc |

### WPF Threats

| STRIDE | Threat | Severity | Detection |
|--------|--------|----------|-----------|
| Spoofing | DLL injection | High | Pattern: LoadLibrary, DllImport |
| Tampering | Config file modification | Medium | Pattern: app.config, appsettings |
| Info Disclosure | Serial port sniffing | Medium | Pattern: SerialPort, COM port |
| DoS | UI thread blocking | Medium | Pattern: Thread.Sleep, .Result |
| EoP | UAC bypass | High | Pattern: requireAdministrator |

## Confidence Scoring

| Score | Meaning |
|:-----:|---------|
| 10 | Definite vulnerability in production code |
| 8-9 | High confidence, production context confirmed |
| 6-7 | Pattern match but context uncertain |
| 4-5 | Possible issue, needs manual verification |
| 0-3 | Low confidence, likely false positive |

**Default threshold: 8** — only high-confidence findings reported.

## False-Positive Exclusions

Files in these paths are automatically excluded or confidence-reduced:
- `test/`, `tests/`, `mock/`, `mocks/`, `example/`, `examples/`
- Files ending in `.test.*` or `.spec.*`
- Debug-only code behind `#ifdef DEBUG`

## Output

**Output Format**:
```
--- Security Review: {feature} -----------------------
Domain    : MCU
Files     : 12 scanned
Threshold : 8/10
Findings  : 3

[CRITICAL] S-MCU-001: Firmware update forgery (9/10)
  File: src/ota/firmware_update.c
  Description: Unsigned firmware updates detected
  Mitigations:
    - Implement secure boot chain
    - Sign firmware with asymmetric keys

[HIGH] I-MCU-001: JTAG/SWD debug port open (8/10)
  File: src/hal/debug_config.h
  Description: Debug port configuration found in production code
  Mitigations:
    - Disable JTAG/SWD in production (fuse bits)

[HIGH] E-MCU-001: Stack overflow risk (8/10)
  File: src/protocol/parser.c
  Description: Unbounded string functions detected
  Mitigations:
    - Use bounded functions (snprintf, strncpy)
------------------------------------------------------
Summary: 1 Critical, 2 High, 0 Medium
```

**Report Path**: `docs/03-analysis/{feature}.security-review.md`

## Integration

### security-architect Agent
The `/security-review` skill can invoke the `security-architect` agent for deeper analysis.
The agent has the embedded STRIDE threat model section for domain-specific review.

### PDCA Check Phase
Security review runs as part of the Check phase, alongside gap analysis.
Auto-suggested after `/pdca analyze` completes.

### /guard Mode
When guard mode is active, security review findings are elevated (threshold lowered to 6).

## Module Dependencies

| Module | Function | Usage |
|--------|----------|-------|
| `lib/quality/embedded-threat-model.js` | `analyze()`, `getStrideSummary()` | Threat detection |
| `agents/security-architect.md` | STRIDE threat model | Deep analysis |

## Usage Examples

```bash
# Review a feature for MCU
/security-review uart-dma

# Review with lower confidence threshold
/security-review kernel-spi --confidence 6

# Force WPF domain
/security-review serial-bridge --domain wpf
```
