package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.Finding;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface FindingRepository extends MongoRepository<Finding, String> {
    List<Finding> findByRemediationStatus(String status);
    List<Finding> findByContractId(String contractId);
}
