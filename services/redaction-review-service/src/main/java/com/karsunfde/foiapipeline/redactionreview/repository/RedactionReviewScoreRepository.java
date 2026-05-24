package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.RedactionReviewScore;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RedactionReviewScoreRepository extends MongoRepository<RedactionReviewScore, String> {
    List<RedactionReviewScore> findByRedactionReviewId(String redaction_reviewId);
    List<RedactionReviewScore> findByRedactionReviewIdAndProposalId(String redaction_reviewId, String proposalId);
    List<RedactionReviewScore> findByEvaluatorId(String evaluatorId);
}
