package com.moneyops.organizations.repository;

import com.moneyops.organizations.entity.RegulatoryProfile;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RegulatoryProfileRepository extends MongoRepository<RegulatoryProfile, String> {

    Optional<RegulatoryProfile> findByOrgIdAndDeletedAtIsNull(String orgId);
}