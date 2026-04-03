# Expected: Docker Log Pipeline Verification Process

## Step 1: Service Health Check
1. Run `docker compose ps` to verify all four services are running and healthy
2. Check sensor-gateway can reach the serial device and MQTT broker
3. Check data-store can connect to PostgreSQL and MQTT broker
4. Confirm no restart loops or crash-back-off in any container

## Step 2: Log Stream Collection
1. Attach to all service logs: `docker compose logs -f --no-log-prefix`
2. Filter sensor-gateway logs for `sensor_read` and `mqtt_publish` events
3. Filter data-store logs for `db_insert` events
4. Capture a minimum 60-second window of continuous log data for analysis

## Step 3: Pipeline Trace Analysis
1. Correlate sensor_read events with corresponding mqtt_publish events by timestamp
2. Verify every mqtt_publish has a matching db_insert within acceptable latency window
3. Check data integrity: sensor values in db_insert match original sensor_read values
4. Validate MQTT QoS=1 delivery guarantees by checking for duplicate or missing messages
5. Measure end-to-end pipeline latency from sensor_read to db_insert completion

## Step 4: Output Verification Report
1. Result summary: total sensor reads, successful MQTT publishes, successful DB inserts
2. Output pipeline success rate as percentage with pass/fail threshold (>99%)
3. List any data loss points where messages were dropped between stages
4. Report average and p99 end-to-end latency measurements
5. Expected Result format: structured JSON report at `./reports/pipeline-qa-report.json`
