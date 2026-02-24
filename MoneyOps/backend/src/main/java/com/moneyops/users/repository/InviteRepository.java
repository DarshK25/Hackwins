package com.moneyops.users.repository;

import com.moneyops.users.entity.Invite;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface InviteRepository extends MongoRepository<Invite, UUID> {

    Optional<Invite> findByToken(String token);

    List<Invite> findAllByOrgId(UUID orgId);

    List<Invite> findAllByOrgIdAndStatus(UUID orgId, Invite.InviteStatus status);

    boolean existsByEmailAndOrgIdAndStatus(String email, UUID orgId, Invite.InviteStatus status);

    // Note: expired invite cleanup should be done via a scheduled task using mongoTemplate
    // (MongoDB does not support JPA-style @Modifying DELETE queries)
}