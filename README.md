# CognigyTester

CognigyTester is a Python-based test harness for validating conversational flows against a Cognigy endpoint and Azure OpenAI. It generates realistic customer scenarios from CSV templates and runs them across multiple mock customer profiles to check whether the bot behaves correctly for different use cases.

Examples of supported scenarios include:
- Submit Meter Reading
- Outage Reporting
- Address Change
- Authentication
- Smart FAQ
- Fallback / escalation cases

## Features
- Loads prompt templates from `prompts.csv`
- Replaces placeholders with customer data from `dummy.csv`
- Runs scenario-based tests across multiple dummy customers
- Sends messages to the Cognigy endpoint
- Uses ChatGPT/Azure OpenAI as a conversational comparison or validation layer
- Stores conversation history and generated IDs for traceability

## Requirements
- Python 3.9+
- pip

Install dependencies:

```bash
pip install -r requirements.txt
