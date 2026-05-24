package com.karsunfde.foiapipeline.foiarequest.repository;

import com.karsunfde.foiapipeline.foiarequest.model.Proposal;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface ProposalRepository extends MongoRepository<Proposal, String> {

    List<Proposal> findByFoiaRequestId(String foia_requestId);

    /** ⚠ Item 10 — vendors should NOT see other vendors' proposals; this
     *  method is the safe one but isn't always used. */
    List<Proposal> findByVendorId(String vendorId);

    /** ⚠ Item 10 — declared but unused. */
    List<Proposal> findByAgencyId(String agencyId);
}
