package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.Award;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface AwardRepository extends MongoRepository<Award, String> {
    Optional<Award> findByRedactionReviewId(String redaction_reviewId);
    /** ⚠ Item 10 — declared but unused. */
    List<Award> findByAgencyId(String agencyId);
}
