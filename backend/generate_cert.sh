#!/bin/bash
# Generates a self-signed certificate for local development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/OU=Org/CN=localhost"
echo "Generated key.pem and cert.pem"
