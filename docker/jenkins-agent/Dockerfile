FROM python:3.12.11-slim-bookworm AS python
FROM node:20.19.3-bookworm-slim AS node
FROM jenkins/inbound-agent:latest-jdk17

USER root

ARG TARGETARCH
ARG TERRAFORM_VERSION=1.9.8

COPY --from=python /usr/local /usr/local
COPY --from=node /usr/local /usr/local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gnupg \
        unzip \
        zip \
    && install -d -m 0755 /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && printf '%s\n' \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && printf '%s' \"$VERSION_CODENAME\") stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-compose-plugin \
    && curl -fsSLo /tmp/terraform.zip \
        "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip" \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && case "$TARGETARCH" in amd64) aws_arch=x86_64 ;; arm64) aws_arch=aarch64 ;; *) exit 1 ;; esac \
    && curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip \
    && npm install --global npm@10.8.2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# The host Docker socket is mounted when this agent is run locally.
RUN groupadd --system docker-host 2>/dev/null || true

USER jenkins
