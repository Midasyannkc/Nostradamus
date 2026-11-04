# ADR 0001: A Kafka-style log in Python instead of a broker

Status: accepted. Context: the build sandbox had no Docker and could not download Kafka. Decision: NostraLog is a partitioned, append-only log with offsets and consumer groups, so delivery semantics (at least once, commit after process) are real and tested. Consequence: the code maps one to one onto Azure Event Hubs with the Kafka API, shown in `terraform/azure`. No claim is made about broker throughput.
