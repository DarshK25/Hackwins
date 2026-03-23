package com.moneyops.users.repository;

import com.moneyops.users.entity.User;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends MongoRepository<User, String> {
    Optional<User> findByIdAndDeletedAtIsNull(String id);
    Optional<User> findByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);
    List<User> findAllByOrgIdAndDeletedAtIsNull(String orgId);
    boolean existsByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);
    void deleteByIdAndOrgId(String id, String orgId); // Note: still keep method for hard delete if needed, or remove

    Optional<User> findByEmailAndOrgIdAndDeletedAtIsNull(String email, String orgId);
    Optional<User> findByEmailAndDeletedAtIsNull(String email);
    Optional<User> findByClerkIdAndDeletedAtIsNull(String clerkId);

    boolean existsByEmailAndOrgIdAndDeletedAtIsNull(String email, String orgId);
    boolean existsByEmailAndDeletedAtIsNull(String email);

    List<User> findAllByOrgIdAndRoleAndDeletedAtIsNull(String orgId, User.Role role);
    List<User> findAllByOrgIdAndStatusAndDeletedAtIsNull(String orgId, User.Status status);

    @org.springframework.data.mongodb.repository.Query("{ 'orgId': ?0, 'deletedAt': null, $or: [ { 'name': { $regex: ?1, $options: 'i' } }, { 'email': { $regex: ?1, $options: 'i' } } ] }")
    List<User> searchByOrgIdWithFilters(String orgId, String query);
}
