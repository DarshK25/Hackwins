package com.moneyops.documents.entity;

import jakarta.annotation.PostConstruct;
import lombok.Data;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Document(collection = "documents")
@CompoundIndex(name = "org_deleted_created_idx", def = "{'orgId': 1, 'deletedAt': 1, 'createdAt': -1}")
@Data
public class MoneyOpsDocument {

    @Id
    private String id;

    @Indexed
    private String orgId;      // Tenant isolation

    private String name;
    private String type;
    private Long size;
    private String firebasePath;
    private String downloadUrl;
    private String mimeType;

    private String uploadedBy; // User ID

    private String linkedEntityType;
    private String linkedEntityId;

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    @CreatedBy
    private String createdBy;

    @LastModifiedBy
    private String updatedBy;

    private LocalDateTime deletedAt;

    private boolean isConfidential = false;
    private String category;
    private String contentSummary;
    private List<String> detectedDeadlines = new ArrayList<>();

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }
}
