// documents/entity/Document.java
package com.moneyops.documents.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID; 

@Entity
@Table(name = "documents")
@Data
public class Document {

    @Id
    @GeneratedValue
    private UUID id;

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

    private LocalDateTime createdAt;
}
