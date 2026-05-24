package com.karsunfde.foiapipeline.redaction_review.repository;

import com.karsunfde.foiapipeline.redaction_review.model.Cpar;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface CparRepository extends MongoRepository<Cpar, String> {
    List<Cpar> findByContractId(String contractId);
    List<Cpar> findByVendorId(String vendorId);
}
