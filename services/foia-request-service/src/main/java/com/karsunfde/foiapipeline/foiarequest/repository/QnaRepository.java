package com.karsunfde.foiapipeline.foia_request.repository;

import com.karsunfde.foiapipeline.foia_request.model.Qna;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface QnaRepository extends MongoRepository<Qna, String> {

    List<Qna> findByFoiaRequestId(String foia_requestId);

    /** ⚠ Item 10 — declared but unused. */
    List<Qna> findByAgencyId(String agencyId);
}
