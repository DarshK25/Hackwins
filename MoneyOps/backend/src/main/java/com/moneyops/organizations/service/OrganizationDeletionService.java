package com.moneyops.organizations.service;

import com.moneyops.audit.entity.AuditLog;
import com.moneyops.clients.entity.Client;
import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.invites.TeamInvite;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.orchestrator.entity.OrchestratorActivity;
import com.moneyops.orchestrator.entity.VoiceConversation;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrganizationDeletionService {

    private final MongoTemplate mongoTemplate;
    private final TeamActionAuthorizationService teamActionAuthorizationService;
    private final UserRepository userRepository;

    @Transactional
    public void deleteOrganizationPermanently(String orgId, String userId, String teamActionCode) {
        teamActionAuthorizationService.assertOwnerCanDeleteOrganization(orgId, userId, teamActionCode);
        User requester = userRepository.findByIdAndDeletedAtIsNull(userId).orElse(null);

        Map<String, Long> deletedCounts = new LinkedHashMap<>();
        deletedCounts.put("audit_logs", deleteByOrgId(orgId, AuditLog.class));
        deletedCounts.put("transactions", deleteByOrgId(orgId, Transaction.class));
        deletedCounts.put("invoices", deleteByOrgId(orgId, Invoice.class));
        deletedCounts.put("clients", deleteByOrgId(orgId, Client.class));
        deletedCounts.put("documents", deleteByOrgId(orgId, MoneyOpsDocument.class));
        deletedCounts.put("regulatory_profiles", deleteByOrgId(orgId, RegulatoryProfile.class));
        deletedCounts.put("invites", deleteByOrgId(orgId, Invite.class));
        deletedCounts.put("team_invites", deleteByOrgId(orgId, TeamInvite.class));
        deletedCounts.put("orchestrator_activities", deleteByOrgId(orgId, OrchestratorActivity.class));
        deletedCounts.put("voice_conversations", deleteByOrgId(orgId, VoiceConversation.class));
        deletedCounts.put("users_by_org", deleteByOrgId(orgId, User.class));
        deletedCounts.put(
                "requester_user_identity",
                deleteUserIdentity(userId, requester != null ? requester.getClerkId() : null)
        );
        deletedCounts.put("business_organizations", deleteOrganizationById(orgId));

        log.info("Permanently deleted organization {} from MongoDB. Counts={}", orgId, deletedCounts);
    }

    private long deleteByOrgId(String orgId, Class<?> entityType) {
        Query query = Query.query(Criteria.where("orgId").is(orgId));
        return mongoTemplate.remove(query, entityType).getDeletedCount();
    }

    private long deleteOrganizationById(String orgId) {
        Query query = Query.query(Criteria.where("_id").is(orgId));
        return mongoTemplate.remove(query, BusinessOrganization.class).getDeletedCount();
    }

    private long deleteUserIdentity(String userId, String clerkId) {
        if ((userId == null || userId.isBlank()) && (clerkId == null || clerkId.isBlank())) {
            return 0;
        }

        Criteria criteria = new Criteria();
        if (userId != null && !userId.isBlank() && clerkId != null && !clerkId.isBlank()) {
            criteria.orOperator(
                    Criteria.where("_id").is(userId),
                    Criteria.where("clerkId").is(clerkId)
            );
        } else if (userId != null && !userId.isBlank()) {
            criteria = Criteria.where("_id").is(userId);
        } else {
            criteria = Criteria.where("clerkId").is(clerkId);
        }

        return mongoTemplate.remove(Query.query(criteria), User.class).getDeletedCount();
    }
}
