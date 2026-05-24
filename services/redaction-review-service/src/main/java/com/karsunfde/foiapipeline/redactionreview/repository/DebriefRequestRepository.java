package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.DebriefRequest;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface DebriefRequestRepository extends MongoRepository<DebriefRequest, String> {
    List<DebriefRequest> findByAwardId(String awardId);
}
