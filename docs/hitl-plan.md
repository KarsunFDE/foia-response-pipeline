# HITL Plan
The sponsor mandate, as received:

> *"Our FOIA officers are buried — every request has to be routed, screened for
> likely exemptions, and checked against past decisions, and the 20-working-day
> clock never stops. We want to pilot AI to triage incoming requests, surface the
> likely-exempt categories, and pull precedent from prior decisions — without ever
> releasing something that should have been withheld, and without an OIP or OIG
> reviewer being able to say the system made a release decision a human was
> supposed to make, or cited an exemption that doesn't exist."*

Some background on FOIA and what the role of a FOIA officer entails:

> *The Freedom of Information Act (FOIA) requires that all public bodies designate one or more
> officials or employees to act as a Freedom of Information Act Officer (FOIA Officer). These
> FOIA Officers (or their designees) shall receive requests for records, ensure that the public body
> responds to the requests in a timely fashion, and issue responses under FOIA. The FOIA Officer
> also shall develop a list of documents or categories of records that the public body shall
> immediately disclose upon request. 5 ILCS 140/3.5(a).*  
> <small>Sourced from [illinoisattorneygeneral.gov](https://illinoisattorneygeneral.gov/Page-Attachments/FOIAPAC/FOIAOfficerFactSheet.pdf)</small>

## Rough Outline
1. AI intakes and analyzes requests 
2. Requests are sorted based on their priority (HITL may be needed to review whether or not the priorty sorting is correct?)
3. Based on the analysis of a given request, search and cite the likely-exempt categories
4. (HITL) Review the determined exemptions
5. Based on the analysis of a given request, look at the relevant prior FOIA decisions or precedent
6. (HITL) Review the prior decisions
7. Based on all of the analyzed information, the AI determines whether the request should be released or withheld
8. (HITL) Review the suggestion and decide on the final decision

## Parallel Developer Workflows
- One workflow can focus on intake, routing, and priority handling.
- One workflow can focus on retrieval of FOIA law, precedent, and exemption grounding.
- One workflow can focus on final recommendation generation, reviewer handoff, and audit visibility.

## Example System Prompts by Phase

### 1. Intake / Triage
You are assisting with FOIA intake triage. Summarize the request, identify likely request type, flag urgency or ambiguity, and recommend routing and priority. Do not make a final release decision.

### 2. Exemption Analysis
You are assisting with FOIA exemption analysis. Review the request and retrieved legal or precedent material. Suggest likely applicable exemptions only when supported by cited authority. If support is weak or unclear, say so explicitly.

### 3. Recommendation Drafting
You are assisting a FOIA officer. Draft a recommendation for release or withholding based only on the analyzed request, cited exemptions, and retrieved precedent. Provide a concise justification. Do not present the result as final. A human reviewer must make the final decision.

### 4. Human Review Handoff
Prepare a concise review summary for a FOIA officer. Include the request summary, likely exemptions, supporting citations, confidence concerns, and the specific decision that requires human approval.
