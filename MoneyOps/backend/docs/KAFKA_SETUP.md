# Kafka setup for MoneyOps backend

The backend can run **with or without Kafka**. By default Kafka is disabled (`KAFKA_ENABLED=false`), so the app starts even when no broker is available. Events are then no-op. When Kafka is enabled, invoice and client domain events are published to topics and the notification consumer processes them.

---

## Option 1: Local Kafka with Docker (recommended for dev)

1. **Start Kafka** (from repo root or `MoneyOps/backend`):

   ```bash
   cd MoneyOps/backend
   docker-compose -f docker-compose.kafka.yml up -d
   ```

2. **Wait until the broker is ready** (healthcheck passes, or wait ~15 seconds).

3. **Configure the backend** via environment or `application.yml`:

   - `KAFKA_ENABLED=true`
   - `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`

   Example (PowerShell):

   ```powershell
   $env:KAFKA_ENABLED="true"
   $env:KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
   mvn spring-boot:run
   ```

   Or add to `application.yml` or a profile (e.g. `application-dev.yml`):

   ```yaml
   spring:
     kafka:
       enabled: true
       bootstrap-servers: localhost:9092
   ```

4. **Stop Kafka** when done:

   ```bash
   docker-compose -f docker-compose.kafka.yml down
   ```

No API keys or secrets are required for this local setup.

---

## Option 2: Managed Kafka (Confluent Cloud, AWS MSK, etc.)

You need: **bootstrap servers**, **security protocol**, and usually **SASL credentials** (API key/secret or IAM). Set these via env vars (or your secret manager) and keep them out of git.

### Confluent Cloud

1. Sign up at [confluent.cloud](https://www.confluent.io/confluent-cloud/).
2. Create a cluster and a **Kafka API key** for the cluster:
   - In the UI: **Data integration** → **API keys** → **Create key** (or use the cluster’s **Settings** → **API keys**).
3. Get the **bootstrap server** list from the cluster (e.g. `pkc-xxxxx.us-east-1.aws.confluent.cloud:9092`).
4. Set in your environment (or `.env`):

   ```bash
   KAFKA_ENABLED=true
   KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.<region>.aws.confluent.cloud:9092
   KAFKA_SECURITY_PROTOCOL=SASL_SSL
   KAFKA_SASL_MECHANISM=PLAIN
   KAFKA_SASL_JAAS_CONFIG=org.apache.kafka.common.security.plain.PlainLoginModule required username="YOUR_API_KEY" password="YOUR_API_SECRET";
   ```

   Replace `YOUR_API_KEY` and `YOUR_API_SECRET` with the key and secret from step 2.  
   **Never commit these values;** use a secret store or CI secrets in production.

### AWS MSK (Amazon Managed Streaming for Apache Kafka)

1. Create an MSK cluster in the AWS console (or Terraform/CloudFormation).
2. Get the **bootstrap brokers** (plaintext or TLS) from the cluster details.
3. For **IAM auth** you’d typically use `AWS_MSK_IAM` and configure the client with AWS credentials (the current backend config is SASL PLAIN; IAM would require extra client config).
4. For **SASL/SCRAM** (username/password):
   - Create a secret in Secrets Manager (or use MSK’s SCRAM identity).
   - Set:

   ```bash
   KAFKA_ENABLED=true
   KAFKA_BOOTSTRAP_SERVERS=b-1.xxxxx.kafka.us-east-1.amazonaws.com:9092
   KAFKA_SECURITY_PROTOCOL=SASL_SSL
   KAFKA_SASL_MECHANISM=SCRAM-SHA-512
   KAFKA_SASL_JAAS_CONFIG=org.apache.kafka.common.security.scram.ScramLoginModule required username="..." password="...";
   ```

   Fetch the username/password from your secret store and inject into `KAFKA_SASL_JAAS_CONFIG`.

### Other managed providers

Use the same pattern:

- `KAFKA_ENABLED=true`
- `KAFKA_BOOTSTRAP_SERVERS=<broker-list>`
- `KAFKA_SECURITY_PROTOCOL=SASL_SSL` (or `SASL_PLAINTEXT` if no TLS)
- `KAFKA_SASL_MECHANISM=PLAIN` (or `SCRAM-SHA-256` / `SCRAM-SHA-512` as required)
- `KAFKA_SASL_JAAS_CONFIG=<JAAS-string>` with the credentials from the provider’s “API key” or “connection” settings.

---

## Env var reference

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_ENABLED` | `false` | Set `true` to enable Kafka producer/consumer. |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Comma-separated broker list. |
| `KAFKA_CONSUMER_GROUP_ID` | `notification-group` | Consumer group for notification listener. |
| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT` | e.g. `SASL_SSL` for managed Kafka. |
| `KAFKA_SASL_MECHANISM` | `PLAIN` | e.g. `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`. |
| `KAFKA_SASL_JAAS_CONFIG` | (empty) | JAAS config string; required when using SASL. |

---

## Topics used

The app uses these topics (created automatically by Kafka on first use if broker allows):

- `invoice-events` – invoice domain events
- `client-events` – client domain events

Consumer group: `notification-group` (or value of `KAFKA_CONSUMER_GROUP_ID`).
