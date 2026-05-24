package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.ContractModification;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface ContractModificationRepository extends MongoRepository<ContractModification, String> {
    List<ContractModification> findByContractIdOrderByModNumberAsc(String contractId);
}
