package com.moneyops.documents.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "documents")
@Data
public class MoneyOpsDocument {

    @Id
    private UUID id = UUID.randomUUID();

    private UUID orgId;
    private String name;
    private String type;
    private Long size;
    private String firebasePath;
    private String downloadUrl;
    private String mimeType;
    private UUID uploadedBy;
    private String linkedEntityType;
    private UUID linkedEntityId;
    private LocalDateTime createdAt = LocalDateTime.now();
}
