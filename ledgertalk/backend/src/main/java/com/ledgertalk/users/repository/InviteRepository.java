// src/main/java/com/ledgertalk/users/repository/InviteRepository.java
package com.ledgertalk.users.repository;

import com.ledgertalk.users.entity.Invite;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface InviteRepository extends JpaRepository<Invite, UUID> {

    Optional<Invite> findByToken(String token);

    List<Invite> findAllByOrgId(UUID orgId);

    List<Invite> findAllByOrgIdAndStatus(UUID orgId, Invite.InviteStatus status);

    @Modifying
    @Query("DELETE FROM Invite i WHERE i.expiresAt < :now")
    void deleteExpiredInvites(@Param("now") LocalDateTime now);

    boolean existsByEmailAndOrgIdAndStatus(String email, UUID orgId, Invite.InviteStatus status);
}