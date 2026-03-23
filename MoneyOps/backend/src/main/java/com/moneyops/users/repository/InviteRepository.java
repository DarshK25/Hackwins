package com.moneyops.users.repository;

import com.moneyops.users.entity.Invite;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface InviteRepository extends MongoRepository<Invite, String> {

    Optional<Invite> findByIdAndDeletedAtIsNull(String id);
    Optional<Invite> findByTokenAndDeletedAtIsNull(String token);
    List<Invite> findAllByOrgIdAndDeletedAtIsNull(String orgId);
    List<Invite> findAllByOrgIdAndStatusAndDeletedAtIsNull(String orgId, Invite.InviteStatus status);
    boolean existsByEmailAndOrgIdAndStatusAndDeletedAtIsNull(String email, String orgId, Invite.InviteStatus status);
}