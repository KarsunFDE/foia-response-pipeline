package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.ContractModification;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface ContractModificationRepository extends MongoRepository<ContractModification, String> {
    List<ContractModification> findByContractIdOrderByModNumberAsc(String contractId);
}
