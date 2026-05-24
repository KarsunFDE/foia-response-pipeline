package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.Award;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface AwardRepository extends MongoRepository<Award, String> {
    Optional<Award> findByRedactionReviewId(String redactionReviewId);
    /** ⚠ Item 10 — declared but unused. */
    List<Award> findByAgencyId(String agencyId);
}
