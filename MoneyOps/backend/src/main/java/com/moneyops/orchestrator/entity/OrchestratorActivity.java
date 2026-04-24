package com.moneyops.orchestrator.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "orchestrator_activities")
@Data
public class OrchestratorActivity {

    @Id
    private String id;

    @Indexed
    private String orgId;        // Tenant isolation

    private String userId;       // Who triggered it

    private String type;         // task_assigned | decision_made | insight_generated | voice_action | error

    private String description;  // Human-readable description

    private String agent;        // Finance Agent | Sales Agent | etc.

    private String status;       // completed | in_progress | failed | pending

    private String intent;       // INVOICE_CREATE | CLIENT_ADD | etc. (from voice)

    private String sessionId;    // Voice session ID (if triggered via voice)

    @Indexed
    private LocalDateTime timestamp;

    @PostConstruct
    public void init() {
        if (this.id == null) this.id = UUID.randomUUID().toString();
        if (this.timestamp == null) this.timestamp = LocalDateTime.now();
    }
}
