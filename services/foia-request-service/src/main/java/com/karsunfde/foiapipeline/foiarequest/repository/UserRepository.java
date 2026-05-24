package com.karsunfde.foiapipeline.foia_request.repository;

import com.karsunfde.foiapipeline.foia_request.model.User;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface UserRepository extends MongoRepository<User, String> {

    Optional<User> findBySub(String sub);

    Optional<User> findByEmail(String email);

    List<User> findByAgencyId(String agencyId);

    List<User> findByRolesContains(String role);
}
