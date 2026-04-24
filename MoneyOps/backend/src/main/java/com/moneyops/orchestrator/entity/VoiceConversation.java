package com.moneyops.orchestrator.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Document(collection = "voice_conversations")
@Data
public class VoiceConversation {

    @Id
    private String id;

    @Indexed
    private String orgId;

    private String userId;

    private String sessionId;

    private String summary;

    private String status; // active | completed | failed

    private LocalDateTime startedAt;

    private LocalDateTime endedAt;

    private Integer duration; // seconds

    private List<Message> messages = new ArrayList<>();

    private List<String> tasksGenerated = new ArrayList<>();

    private Integer totalTurns = 0;

    @PostConstruct
    public void init() {
        if (this.id == null) this.id = UUID.randomUUID().toString();
        if (this.startedAt == null) this.startedAt = LocalDateTime.now();
        if (this.status == null) this.status = "active";
    }

    @Data
    public static class Message {
        private String role;     // user | assistant
        private String content;
        private LocalDateTime timestamp;
        private String intent;   // optional, set for user messages
    }
}
