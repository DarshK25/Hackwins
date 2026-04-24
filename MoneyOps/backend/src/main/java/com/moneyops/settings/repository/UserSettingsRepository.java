package com.moneyops.settings.repository;

import com.moneyops.settings.entity.UserSettings;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserSettingsRepository extends MongoRepository<UserSettings, String> {
    Optional<UserSettings> findByOrgIdAndUserId(String orgId, String userId);
}
