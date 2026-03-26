package com.moneyops.config;

import com.mongodb.MongoClientSettings;
import org.bson.UuidRepresentation;
import org.bson.types.Binary;
import org.springframework.boot.autoconfigure.mongo.MongoClientSettingsBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Base64;
import java.util.UUID;

/**
 * MongoConfig — permanent fix for UUID binary subType mismatch and legacy Binary-to-String conversions.
 *
 * History of the bug:
 *   All MoneyOps MongoDB documents store UUIDs as BSON Binary subType 03
 *   (JAVA_LEGACY — the format used by the MongoDB Java driver <= 3.x and
 *   Spring Data MongoDB <= 2.x).
 *
 *   Spring Data MongoDB 4.x (bundled in Spring Boot 3.x) defaults to
 *   UuidRepresentation.STANDARD (subType 04).
 *
 * Fix (Update v2):
 *   Standardized to UUID as plain strings or subType 04 (STANDARD) for cross-platform
 *   compatibility (Python, etc.). This ensures all new documents use the modern format.
 * 
 * Fix (Update v3 - BinaryToStringConverter):
 *   When the application switched entity ID fields from java.util.UUID to java.lang.String
 *   for Clerk compatibility, Spring Data threw ConverterNotFoundException whenever reading
 *   existing legacy documents containing BSON Binary (UUIDs) into String fields.
 *   The BinaryToStringConverter seamlessly translates DB Binary UUIDs into Strings on the fly.
 */
@Configuration
public class MongoConfig {

    @Bean
    public MongoClientSettingsBuilderCustomizer uuidRepresentationCustomizer() {
        return builder -> builder.uuidRepresentation(UuidRepresentation.STANDARD);
    }

    @Bean
    public MongoCustomConversions customConversions() {
        return new MongoCustomConversions(Arrays.asList(new BinaryToStringConverter()));
    }

    /**
     * Converts BSON Binary fields back into java.lang.String seamlessly, 
     * resolving the ConverterNotFoundException when legacy UUIDs are mapped 
     * onto String properties.
     */
    public static class BinaryToStringConverter implements Converter<Binary, String> {
        @Override
        public String convert(Binary source) {
            byte[] bytes = source.getData();
            if (bytes.length == 16) {
                ByteBuffer bb = ByteBuffer.wrap(bytes);
                long mostSigBits = bb.getLong();
                long leastSigBits = bb.getLong();
                
                // If it was a legacy Java UUID (subType 03), the byte order is little-endian. 
                // However, since we set Java UUIDs manually before, we attempt standard parsing.
                // Assuming standard UUID bytes:
                if (source.getType() == org.bson.BsonBinarySubType.UUID_LEGACY.getValue()) {
                    // Legacy Java UUID was stored with Little Endian byte fragments.
                    // We must reverse them back if it was saved by legacy MongoDB Java Driver.
                    bb.order(java.nio.ByteOrder.LITTLE_ENDIAN);
                    bb.rewind();
                    long msb = bb.getLong();
                    long lsb = bb.getLong();
                    return new UUID(msb, lsb).toString();
                } else {
                    return new UUID(mostSigBits, leastSigBits).toString();
                }
            }
            // Fallback for non-UUID binaries
            return java.util.Base64.getEncoder().encodeToString(bytes);
        }
    }
}
