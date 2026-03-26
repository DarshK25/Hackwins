package com.moneyops.invites;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface TeamInviteRepository extends MongoRepository<TeamInvite, String> {
    Optional<TeamInvite> findByToken(String token);
    Optional<TeamInvite> findByEmailAndOrgId(String email, String orgId);
}
