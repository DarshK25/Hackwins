// src/main/java/com/ledgertalk/clients/repository/ClientRepository.java
package com.ledgertalk.clients.repository;

import com.ledgertalk.clients.entity.Client;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ClientRepository extends JpaRepository<Client, UUID> {

    Optional<Client> findByIdAndOrgId(UUID id, UUID orgId);

    List<Client> findAllByOrgId(UUID orgId);

    boolean existsByIdAndOrgId(UUID id, UUID orgId);

    void deleteByIdAndOrgId(UUID id, UUID orgId);

    Optional<Client> findByEmailAndOrgId(String email, UUID orgId);

    boolean existsByEmailAndOrgId(String email, UUID orgId);

    @Query("SELECT c FROM Client c WHERE c.orgId = :orgId AND " +
           "(LOWER(c.name) LIKE LOWER(CONCAT('%', :search, '%')) OR " +
           "LOWER(c.email) LIKE LOWER(CONCAT('%', :search, '%')))")
    List<Client> searchByOrgIdWithFilters(@Param("orgId") UUID orgId, @Param("search") String search);

    List<Client> findAllByOrgIdAndStatus(UUID orgId, Client.Status status);
}