#!/usr/bin/env bash
# Seed the local MongoDB with a few demo FOIA requests.
# Usage:  ./scripts/seed-mongo.sh   (run after `docker-compose up`)

set -euo pipefail

MONGO_URL="${MONGO_URL:-mongodb://app:app_dev_password@localhost:27017}"

cat <<'EOF' | docker run --rm -i --network host mongo:7 mongosh "$MONGO_URL/foia_response_pipeline?authSource=admin"
db.foia_requests.insertMany([
  {
    agencyId: "DOJ-OIP",
    trackingNumber: "DOJ-2026-0142",
    title: "Deliberative memos on FOIA backlog policy",
    recordsSought: "<p>All inter- and intra-agency memoranda discussing the 2025 FOIA backlog-reduction policy.</p>",
    requesterName: "J. Alvarez",
    requesterOrg: "The Sunlight Beacon",
    requesterType: "news_media_educational_scientific",
    feeCategory: "news_media_educational_scientific",
    feeWaiverRequested: true,
    expeditedProcessingRequested: false,
    status: "EXEMPTION_ANALYSIS",
    receivedDate: new Date(),
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    agencyId: "DOJ-OIP",
    trackingNumber: "DOJ-2026-0203",
    title: "Vendor pricing in cloud-services contract files",
    recordsSought: "Unit-pricing tables and proprietary cost narratives submitted by the awardee of GS-35F-0001V.",
    requesterName: "Initech Research LLC",
    requesterOrg: "Initech Research LLC",
    requesterType: "commercial",
    feeCategory: "commercial",
    feeWaiverRequested: false,
    expeditedProcessingRequested: false,
    status: "INTAKE_TRIAGE",
    receivedDate: new Date(),
    createdAt: new Date(),
    updatedAt: new Date()
  }
]);
print("Seeded " + db.foia_requests.countDocuments() + " foia_requests.");
EOF
