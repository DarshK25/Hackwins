package com.moneyops.orchestrator.repository;

import com.moneyops.orchestrator.entity.OrchestratorActivity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface OrchestratorActivityRepository extends MongoRepository<OrchestratorActivity, String> {

    List<OrchestratorActivity> findByOrgIdOrderByTimestampDesc(String orgId);

    Page<OrchestratorActivity> findByOrgIdOrderByTimestampDesc(String orgId, Pageable pageable);

    List<OrchestratorActivity> findByOrgIdAndAgentOrderByTimestampDesc(String orgId, String agent);

    List<OrchestratorActivity> findByOrgIdAndSessionIdOrderByTimestampAsc(String orgId, String sessionId);

    List<OrchestratorActivity> findByOrgIdAndTimestampAfterOrderByTimestampDesc(String orgId, LocalDateTime after);
}
