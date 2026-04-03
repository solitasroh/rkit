# Docker Log Analysis: MCU Sensor Data Pipeline Verification

I need to verify our end-to-end sensor data pipeline using Docker log analysis.
The pipeline flows: STM32 sensor read -> MQTT publish -> database store.

## Docker Services
- `sensor-gateway`: Reads I2C sensor data from STM32 via serial, publishes to MQTT
- `mqtt-broker`: Mosquitto MQTT broker on port 1883
- `data-store`: Subscribes to MQTT topics, writes to PostgreSQL database
- `postgres`: PostgreSQL 15 database for persistent sensor storage

## Expected JSON Log Format
- Sensor read: `{"service":"sensor-gateway","event":"sensor_read","sensor":"BME280","temp":23.5,"humidity":45.2,"ts":"2026-04-03T10:00:00Z"}`
- MQTT publish: `{"service":"sensor-gateway","event":"mqtt_publish","topic":"sensors/bme280","qos":1,"status":"ok"}`
- DB insert: `{"service":"data-store","event":"db_insert","table":"sensor_readings","rows":1,"status":"ok"}`

Please trace the full pipeline through Docker logs and verify data integrity at each stage.
