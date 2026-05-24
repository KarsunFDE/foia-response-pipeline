package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.Deliverable;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface DeliverableRepository extends MongoRepository<Deliverable, String> {
    List<Deliverable> findByContractId(String contractId);
}
