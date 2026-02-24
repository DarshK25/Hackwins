package com.moneyops.config;

import com.mongodb.MongoClientSettings;
import org.bson.UuidRepresentation;
import org.springframework.boot.autoconfigure.mongo.MongoClientSettingsBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MongoConfig — permanent fix for UUID binary subType mismatch.
 *
 * History of the bug:
 *   All MoneyOps MongoDB documents store UUIDs as BSON Binary subType 03
 *   (JAVA_LEGACY — the format used by the MongoDB Java driver ≤ 3.x and
 *   Spring Data MongoDB ≤ 2.x).
 *
 *   Spring Data MongoDB 4.x (bundled in Spring Boot 3.x) defaults to
 *   UuidRepresentation.STANDARD (subType 04). This means:
 *   - Every UUID @Id and UUID query field gets serialised as subType 04.
 *   - The DB still has subType 03 documents.
 *   - Result: ALL UUID-based queries silently return 0 rows — including
 *     findByOrgId(), findById(), getAllClients(), etc.
 *
 * Fix:
 *   Register a MongoClientSettingsBuilderCustomizer that switches the codec
 *   back to JAVA_LEGACY (subType 03). This is the PERMANENT fix — it matches
 *   every existing document without any data migration.
 *
 * Side-effects resolved by this fix:
 *   • "Client not found" errors when looking up by orgId.
 *   • Voice-agent invoice creation failures (org/client lookup returning empty).
 *   • Any future query using a UUID field over a pre-existing collection.
 */
@Configuration
public class MongoConfig {

    @Bean
    public MongoClientSettingsBuilderCustomizer uuidRepresentationCustomizer() {
        return builder -> builder.uuidRepresentation(UuidRepresentation.JAVA_LEGACY);
    }
}

