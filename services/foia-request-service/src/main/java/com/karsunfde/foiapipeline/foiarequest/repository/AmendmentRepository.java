package com.karsunfde.foiapipeline.foia_request.repository;

import com.karsunfde.foiapipeline.foia_request.model.Amendment;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface AmendmentRepository extends MongoRepository<Amendment, String> {

    List<Amendment> findByFoiaRequestIdOrderByNumberAsc(String foia_requestId);

    /** ⚠ Item 10 — declared but unused. */
    List<Amendment> findByAgencyId(String agencyId);
}
