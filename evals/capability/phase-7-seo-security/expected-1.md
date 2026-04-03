## Step 1: Signature Verification Process

1. Build server signs firmware binary with ECDSA-P256 private key
2. Signature (64 bytes) is appended to the firmware image header
3. Device extracts public key from read-only flash (OTP or write-protected sector)
4. Device computes SHA-256 hash of the firmware binary
5. Device performs ECDSA signature validation against the computed hash
6. If validation fails, the firmware image is rejected and the update is aborted

Security consideration: The public key must be stored in a tamper-resistant location.
On STM32H7, use OTP (One-Time Programmable) bytes or RDP Level 1 protected flash.

```c
typedef struct {
    uint32_t magic;           /* 0x46575550 "FWUP" */
    uint32_t version;         /* Monotonic version counter */
    uint32_t image_size;      /* Firmware binary size */
    uint8_t  sha256[32];      /* SHA-256 of firmware binary */
    uint8_t  signature[64];   /* ECDSA-P256 signature */
} FirmwareHeader_t;

typedef enum {
    OTA_VERIFY_OK = 0,
    OTA_VERIFY_ERR_SIGNATURE,
    OTA_VERIFY_ERR_HASH,
    OTA_VERIFY_ERR_VERSION,
    OTA_VERIFY_ERR_SIZE
} OtaVerifyResult_t;
```

## Step 2: Encrypted Channel Setup

1. Device establishes TLS 1.3 connection to firmware update server
2. Server certificate is validated against a pinned CA certificate stored in device flash
3. Firmware image is downloaded in chunks (4KB blocks) over the encrypted channel
4. Each chunk is written to the inactive flash bank after decryption
5. Connection timeout and retry policy: 30s timeout, 3 retries with exponential back-off

Security validation checklist:
- Certificate pinning prevents man-in-the-middle attacks
- TLS 1.3 ensures forward secrecy (no session replay)
- Chunk-based download allows progress tracking and resume after connection loss
- No plaintext firmware data touches the wire at any point

## Step 3: Rollback Protection Mechanism

1. Each firmware version carries a monotonic counter in the image header
2. Current counter value is stored in STM32H7 OTP fuse bits (one-way increment only)
3. During validation, the new image counter must be strictly greater than the stored counter
4. After successful boot of new firmware, the OTP counter is incremented to match
5. If new firmware fails to boot (watchdog timeout), device reverts to previous bank

Anti-rollback security rules:
- Version counter in OTP cannot be decremented (hardware-enforced)
- Replay attacks with old firmware versions are blocked by counter comparison
- Dual-bank flash allows safe fallback without erasing the known-good image

```c
bool validate_version_counter(uint32_t new_version)
{
    uint32_t current = read_otp_version_counter();
    if (new_version <= current)
    {
        /* Downgrade or replay attempt - reject */
        return false;
    }
    return true;
}

void commit_version_counter(uint32_t new_version)
{
    /* Write to OTP - irreversible operation */
    write_otp_version_counter(new_version);
}
```

## Step 4: Secure Boot Chain Validation

1. ROM bootloader verifies first-stage bootloader signature (hardware root of trust)
2. First-stage bootloader verifies application firmware signature
3. Each stage uses its own key pair for chain-of-trust isolation
4. JTAG/SWD debug ports are disabled in production via RDP Level 2 or TZEN
5. Watchdog timer ensures failed firmware triggers automatic rollback

## Step 5: Security Checklist

| Check Item | Status | Security Impact |
|------------|--------|-----------------|
| ECDSA-P256 signature validation | Required | Prevents tampered firmware |
| SHA-256 hash verification | Required | Detects corruption |
| TLS 1.3 encrypted transport | Required | Prevents MITM interception |
| Certificate pinning | Required | Prevents CA compromise |
| OTP monotonic version counter | Required | Prevents rollback attacks |
| Dual-bank flash fallback | Required | Ensures recovery from bad update |
| JTAG/SWD disabled in production | Required | Prevents physical debug access |
| Watchdog-based rollback | Required | Auto-recovery from bricked firmware |
| Firmware header magic validation | Required | Rejects malformed images |
| Flash write protection on key storage | Required | Protects signing keys |

## Summary

- Four-layer security model: signature, encryption, anti-rollback, secure boot chain
- ECDSA-P256 signature with SHA-256 hash provides firmware authenticity validation
- TLS 1.3 with certificate pinning secures the transport channel
- OTP-based monotonic counter provides hardware-enforced rollback protection
- Dual-bank flash enables safe update with automatic fallback on failure
