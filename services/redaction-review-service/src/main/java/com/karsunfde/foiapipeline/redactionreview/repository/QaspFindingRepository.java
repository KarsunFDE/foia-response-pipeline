package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.QaspFinding;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface QaspFindingRepository extends MongoRepository<QaspFinding, String> {
    List<QaspFinding> findByContractId(String contractId);
}
