package com.moneyops.organizations.repository;

import com.moneyops.organizations.entity.RegulatoryProfile;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;
import java.util.UUID;

public interface RegulatoryProfileRepository extends MongoRepository<RegulatoryProfile, UUID> {

    Optional<RegulatoryProfile> findByOrgId(UUID orgId);
}