package com.moneyops.orchestrator.repository;

import com.moneyops.orchestrator.entity.VoiceConversation;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface VoiceConversationRepository extends MongoRepository<VoiceConversation, String> {

    List<VoiceConversation> findByOrgIdOrderByStartedAtDesc(String orgId);

    List<VoiceConversation> findByOrgIdAndStartedAtAfterOrderByStartedAtDesc(
            String orgId, LocalDateTime after);

    List<VoiceConversation> findBySessionIdAndOrgIdOrderByStartedAtDesc(String sessionId, String orgId);

    long countByOrgIdAndStartedAtAfter(String orgId, LocalDateTime after);
}
