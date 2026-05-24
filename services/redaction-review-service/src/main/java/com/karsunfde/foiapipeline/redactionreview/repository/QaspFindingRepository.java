package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.QaspFinding;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface QaspFindingRepository extends MongoRepository<QaspFinding, String> {
    List<QaspFinding> findByContractId(String contractId);
}
