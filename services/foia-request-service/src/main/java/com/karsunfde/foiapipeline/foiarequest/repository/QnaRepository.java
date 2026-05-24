package com.karsunfde.foiapipeline.foiarequest.repository;

import com.karsunfde.foiapipeline.foiarequest.model.Qna;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface QnaRepository extends MongoRepository<Qna, String> {

    List<Qna> findByFoiaRequestId(String foiaRequestId);

    /** ⚠ Item 10 — declared but unused. */
    List<Qna> findByAgencyId(String agencyId);
}
