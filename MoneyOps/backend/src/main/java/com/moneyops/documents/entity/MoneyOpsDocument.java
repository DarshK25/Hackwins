package com.moneyops.documents.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "documents")
@Data
public class MoneyOpsDocument {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    private String name;
    private String type;
    private Long size;
    private String firebasePath;
    private String downloadUrl;
    private String mimeType;
    
    private String uploadedBy; // User ID (String)
    
    private String linkedEntityType;
    private String linkedEntityId; // String ID

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
    private java.util.List<String> detectedDeadlines;

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }
}
