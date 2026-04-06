package com.moneyops.memory.repository;

import com.moneyops.memory.entity.OrgMemory;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface OrgMemoryRepository extends MongoRepository<OrgMemory, String> {
    Optional<OrgMemory> findByOrgId(String orgId);
}
