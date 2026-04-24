package com.moneyops.organizations.service;

import com.mongodb.client.result.DeleteResult;
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
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;

import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OrganizationDeletionServiceTest {

    @Mock
    private MongoTemplate mongoTemplate;

    @Mock
    private TeamActionAuthorizationService teamActionAuthorizationService;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private OrganizationDeletionService organizationDeletionService;

    @Test
    void deleteOrganizationPermanentlyRemovesWorkspaceDocuments() {
        User requester = new User();
        requester.setId("user-456");
        requester.setClerkId("clerk-456");

        when(mongoTemplate.remove(any(Query.class), eq(AuditLog.class))).thenReturn(DeleteResult.acknowledged(2));
        when(mongoTemplate.remove(any(Query.class), eq(Transaction.class))).thenReturn(DeleteResult.acknowledged(3));
        when(mongoTemplate.remove(any(Query.class), eq(Invoice.class))).thenReturn(DeleteResult.acknowledged(4));
        when(mongoTemplate.remove(any(Query.class), eq(Client.class))).thenReturn(DeleteResult.acknowledged(5));
        when(mongoTemplate.remove(any(Query.class), eq(MoneyOpsDocument.class))).thenReturn(DeleteResult.acknowledged(6));
        when(mongoTemplate.remove(any(Query.class), eq(RegulatoryProfile.class))).thenReturn(DeleteResult.acknowledged(1));
        when(mongoTemplate.remove(any(Query.class), eq(Invite.class))).thenReturn(DeleteResult.acknowledged(2));
        when(mongoTemplate.remove(any(Query.class), eq(TeamInvite.class))).thenReturn(DeleteResult.acknowledged(1));
        when(mongoTemplate.remove(any(Query.class), eq(OrchestratorActivity.class))).thenReturn(DeleteResult.acknowledged(3));
        when(mongoTemplate.remove(any(Query.class), eq(VoiceConversation.class))).thenReturn(DeleteResult.acknowledged(2));
        when(mongoTemplate.remove(any(Query.class), eq(User.class))).thenReturn(DeleteResult.acknowledged(4));
        when(mongoTemplate.remove(any(Query.class), eq(BusinessOrganization.class))).thenReturn(DeleteResult.acknowledged(1));
        when(userRepository.findByIdAndDeletedAtIsNull("user-456")).thenReturn(Optional.of(requester));

        organizationDeletionService.deleteOrganizationPermanently("org-123", "user-456", "4321");

        verify(teamActionAuthorizationService).assertOwnerCanDeleteOrganization("org-123", "user-456", "4321");
        verify(userRepository).findByIdAndDeletedAtIsNull("user-456");
        verify(mongoTemplate).remove(any(Query.class), eq(AuditLog.class));
        verify(mongoTemplate).remove(any(Query.class), eq(Transaction.class));
        verify(mongoTemplate).remove(any(Query.class), eq(Invoice.class));
        verify(mongoTemplate).remove(any(Query.class), eq(Client.class));
        verify(mongoTemplate).remove(any(Query.class), eq(MoneyOpsDocument.class));
        verify(mongoTemplate).remove(any(Query.class), eq(RegulatoryProfile.class));
        verify(mongoTemplate).remove(any(Query.class), eq(Invite.class));
        verify(mongoTemplate).remove(any(Query.class), eq(TeamInvite.class));
        verify(mongoTemplate).remove(any(Query.class), eq(OrchestratorActivity.class));
        verify(mongoTemplate).remove(any(Query.class), eq(VoiceConversation.class));
        verify(mongoTemplate, times(2)).remove(any(Query.class), eq(User.class));
        verify(mongoTemplate).remove(any(Query.class), eq(BusinessOrganization.class));
    }
}
