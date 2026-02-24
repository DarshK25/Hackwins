package com.moneyops.users.repository;

import com.moneyops.users.entity.User;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends MongoRepository<User, UUID> {

    Optional<User> findByIdAndOrgId(UUID id, UUID orgId);
    List<User> findAllByOrgId(UUID orgId);
    boolean existsByIdAndOrgId(UUID id, UUID orgId);
    void deleteByIdAndOrgId(UUID id, UUID orgId);

    Optional<User> findByEmailAndOrgId(String email, UUID orgId);
    Optional<User> findByEmail(String email);
    Optional<User> findByClerkId(String clerkId);

    boolean existsByEmailAndOrgId(String email, UUID orgId);
    boolean existsByEmail(String email);

    List<User> findAllByOrgIdAndRole(UUID orgId, User.Role role);
    List<User> findAllByOrgIdAndStatus(UUID orgId, User.Status status);

    @org.springframework.data.mongodb.repository.Query("{ 'orgId': ?0, $or: [ { 'firstName': { $regex: ?1, $options: 'i' } }, { 'lastName': { $regex: ?1, $options: 'i' } }, { 'email': { $regex: ?1, $options: 'i' } } ] }")
    List<User> searchByOrgIdWithFilters(UUID orgId, String query);
}
