package com.moneyops.invites;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.index.Indexed;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Document(collection = "team_invites")
public class TeamInvite {
    @Id
    private String id;
    
    private String email;
    private String orgId;
    private String role;
    
    @Indexed(unique = true)
    private String token;
    
    private String status; // PENDING, ACCEPTED, EXPIRED

    @Indexed(expireAfterSeconds = 0) // TTL index based on expiresAt
    private Instant expiresAt;
    
    private Instant createdAt;
}
