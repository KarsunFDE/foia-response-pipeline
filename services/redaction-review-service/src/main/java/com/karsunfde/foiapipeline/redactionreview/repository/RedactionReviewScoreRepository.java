package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.RedactionReviewScore;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RedactionReviewScoreRepository extends MongoRepository<RedactionReviewScore, String> {
    List<RedactionReviewScore> findByRedactionReviewId(String redactionReviewId);
    List<RedactionReviewScore> findByRedactionReviewIdAndProposalId(String redactionReviewId, String proposalId);
    List<RedactionReviewScore> findByEvaluatorId(String evaluatorId);
}
