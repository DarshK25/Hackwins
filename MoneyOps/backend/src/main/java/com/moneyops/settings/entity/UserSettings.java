package com.moneyops.settings.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "user_settings")
@CompoundIndex(name = "org_user_idx", def = "{'orgId': 1, 'userId': 1}", unique = true)
public class UserSettings {

    @Id
    private String id;

    private String orgId;
    private String userId;

    private String firstName;
    private String lastName;
    private String professionalTitle;
    private String phone;

    private boolean invoiceDue = true;
    private boolean paymentReceived = true;
    private boolean clientUpdates = false;
    private boolean weeklyReport = true;
    private boolean systemAlerts = true;

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}
