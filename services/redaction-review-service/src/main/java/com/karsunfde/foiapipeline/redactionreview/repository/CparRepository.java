package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.Cpar;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface CparRepository extends MongoRepository<Cpar, String> {
    List<Cpar> findByContractId(String contractId);
    List<Cpar> findByVendorId(String vendorId);
}
