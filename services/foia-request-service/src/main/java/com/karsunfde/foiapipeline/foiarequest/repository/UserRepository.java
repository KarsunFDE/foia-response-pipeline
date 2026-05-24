package com.karsunfde.foiapipeline.foiarequest.repository;

import com.karsunfde.foiapipeline.foiarequest.model.User;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface UserRepository extends MongoRepository<User, String> {

    Optional<User> findBySub(String sub);

    Optional<User> findByEmail(String email);

    List<User> findByAgencyId(String agencyId);

    List<User> findByRolesContains(String role);
}
