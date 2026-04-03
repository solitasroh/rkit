# Expected: Zero Script QA UART Communication Test Process

## Step 1: Docker Log Collection
1. Start Docker Compose environment with `docker compose up -d`
2. Attach to the log-collector service: `docker compose logs -f log-collector`
3. Verify all three services (serial-bridge, log-collector, test-runner) are healthy
4. Confirm structured JSON logging is active and streams are captured

## Step 2: Test Trigger Execution
1. Send test commands via the serial bridge to the STM32 target
2. Execute TX test sequence: transmit 100 structured JSON packets at 115200 baud
3. Execute RX test sequence: wait for echo-back responses from the STM32 firmware
4. Inject deliberate error cases (malformed CRC, oversized payload) for negative testing

## Step 3: Log Pattern Analysis
1. Grep collected logs for expected TX patterns: `{"event":"tx_complete",...}`
2. Grep collected logs for expected RX patterns: `{"event":"rx_complete",...,"crc_valid":true}`
3. Count total TX packets sent vs RX packets received to compute success rate
4. Verify CRC-16 checksums match between TX and RX pairs
5. Check timing constraints: round-trip latency must be under 50ms per packet

## Step 4: Issue Detection
1. Identify timeout errors from logs: `{"event":"rx_error","type":"timeout",...}`
2. Detect CRC mismatch errors indicating data corruption on the serial link
3. Flag dropped packets where TX count exceeds RX count beyond acceptable threshold
4. Check for buffer overflow warnings in the serial-bridge service logs

## Step 5: Test Report Generation
1. Output a structured test report summarizing all findings
2. Result summary table: total TX, total RX, success rate, average latency
3. List all detected issues with severity classification (critical/warning/info)
4. Include pass/fail verdict based on acceptance criteria (>99% success rate, <50ms latency)
5. Expected Output format: JSON report file saved to `./reports/uart-qa-report.json`
