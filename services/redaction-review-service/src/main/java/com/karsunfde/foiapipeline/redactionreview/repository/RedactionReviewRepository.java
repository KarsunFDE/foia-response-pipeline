package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.RedactionReview;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RedactionReviewRepository extends MongoRepository<RedactionReview, String> {
    List<RedactionReview> findByFoiaRequestId(String foia_requestId);
    /** ⚠ Item 10 — declared but list endpoints often skip. */
    List<RedactionReview> findByAgencyId(String agencyId);
}
