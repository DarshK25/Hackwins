package com.moneyops.documents.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class DocumentUploadDTO {
    private String orgId;
    private String name;
    private String type;
    private String mimeType;
    private String linkedEntityType;
    private String linkedEntityId;
    private String category;
    private String contentSummary;
    private List<String> detectedDeadlines = new ArrayList<>();
    private Boolean isConfidential;
}
