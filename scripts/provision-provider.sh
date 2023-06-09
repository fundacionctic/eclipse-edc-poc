#!/usr/bin/env bash

set -e
set -x

BASE_DIR=/vagrant

# Both the provider and consumer share the same /vagrant directory.
# Therefore, we only need to clean and build the connector JAR once.
cd ${BASE_DIR}
task clean
task create-example-certs-provider
task move-connector-jar

cd ${BASE_DIR}/mock-component
docker compose up -d --build --wait

cd ${BASE_DIR}
docker compose -f ./docker-compose-provider.yml up -d --build --wait