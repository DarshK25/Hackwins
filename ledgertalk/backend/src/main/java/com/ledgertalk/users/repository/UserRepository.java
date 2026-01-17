// src/main/java/com/ledgertalk/users/repository/UserRepository.java
package com.ledgertalk.users.repository;

import com.ledgertalk.users.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByIdAndOrgId(UUID id, UUID orgId);

    List<User> findAllByOrgId(UUID orgId);

    boolean existsByIdAndOrgId(UUID id, UUID orgId);

    void deleteByIdAndOrgId(UUID id, UUID orgId);

    Optional<User> findByEmailAndOrgId(String email, UUID orgId);

    boolean existsByEmailAndOrgId(String email, UUID orgId);

    @Query("SELECT u FROM User u WHERE u.orgId = :orgId AND " +
           "(LOWER(u.name) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(u.email) LIKE LOWER(CONCAT('%', :search, '%')))")
    List<User> searchByOrgIdWithFilters(@Param("orgId") UUID orgId, @Param("search") String search);

    List<User> findAllByOrgIdAndRole(UUID orgId, String role);

    List<User> findAllByOrgIdAndStatus(UUID orgId, String status);
}