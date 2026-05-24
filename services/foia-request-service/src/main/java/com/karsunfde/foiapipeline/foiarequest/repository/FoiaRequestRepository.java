package com.karsunfde.foiapipeline.foiarequest.repository;

import com.karsunfde.foiapipeline.foiarequest.model.FoiaRequest;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

/**
 * ⚠ DELIBERATE — Item 10:
 *   {@code findAll()} returns foia_requests across ALL agencies. There is a
 *   {@code findByAgencyId} method declared below — it just isn't called from
 *   {@code FoiaRequestService}. Cohort fixes in W2 Wed by switching all
 *   reads to {@code findByAgencyId} (and resolving agency from JWT).
 */
public interface FoiaRequestRepository extends MongoRepository<FoiaRequest, String> {

    /** Declared but not used — the cohort discovers and wires this up. */
    List<FoiaRequest> findByAgencyId(String agencyId);
}
