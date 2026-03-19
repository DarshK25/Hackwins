package com.moneyops.clients.repository;

import com.moneyops.clients.entity.Client;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ClientRepository extends MongoRepository<Client, String> {

    boolean existsByEmail(String email);

    Optional<Client> findByIdAndOrgId(String id, UUID orgId);

    List<Client> findAllByOrgId(UUID orgId);

    boolean existsByIdAndOrgId(String id, UUID orgId);

    Optional<Client> findByEmailAndOrgId(String email, UUID orgId);

    boolean existsByEmailAndOrgId(String email, UUID orgId);

    List<Client> findAllByOrgIdAndStatus(UUID orgId, Client.Status status);

    void deleteByIdAndOrgId(String id, UUID orgId);

    @org.springframework.data.mongodb.repository.Query("{ 'orgId': ?0, $or: [ { 'name': { $regex: ?1, $options: 'i' } }, { 'email': { $regex: ?1, $options: 'i' } } ] }")
    List<Client> searchByOrgIdWithFilters(UUID orgId, String query);
}