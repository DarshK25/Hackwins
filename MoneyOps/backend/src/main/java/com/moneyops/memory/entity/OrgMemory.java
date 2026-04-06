package com.moneyops.memory.entity;

import jakarta.annotation.PostConstruct;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Document(collection = "org_memory")
@Data
public class OrgMemory {

    @Id
    private String id;

    @Indexed(unique = true)
    private String orgId;

    private List<MemoryItem> memories = new ArrayList<>();

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }

    @Data
    public static class MemoryItem {
        private String id;
        private String type;
        private String content;
        private String source;
        private LocalDateTime createdAt;
        private LocalDateTime lastReferencedAt;
        private List<String> tags = new ArrayList<>();
    }
}
