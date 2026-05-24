package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.DebriefRequest;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface DebriefRequestRepository extends MongoRepository<DebriefRequest, String> {
    List<DebriefRequest> findByAwardId(String awardId);
}
