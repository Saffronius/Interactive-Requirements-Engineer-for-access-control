# Policy Requirements Engineer

A Python-based tool that converts natural language AWS IAM policy requirements into structured policy requirements checklists and SimplePolicyTalk (SPT) DSL policies using OpenAI's GPT-4.

## Overview

This tool helps bridge the gap between natural language policy requirements and formal AWS IAM policies by:
1. Converting natural language requirements into structured checklists
2. Identifying ambiguities and missing information
3. Generating SPT (SimplePolicyTalk) policy statements
4. Supporting test case generation for policy validation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

## Code Structure

### PolicyRequirementsEngineer Class

The main class that handles all policy requirement processing.

#### Initialization
```python
def __init__(self, api_key: str = None)
```
- Loads environment variables from `.env` file
- Accepts an optional API key parameter
- Falls back to environment variable if no key provided
- Initializes OpenAI client

#### Natural Language to Checklist Conversion
```python
def nl_to_checklist_prompt(self, nl_requirement: str) -> str
```
Generates a prompt for converting natural language requirements into a structured checklist format. The checklist includes:
- Metadata about the requirement's completeness and ambiguity
- Policy intent analysis
- Detailed requirements breakdown including:
  - Effect (ALLOW/DENY)
  - Principal specifications
  - Action definitions
  - Resource specifications
  - Condition requirements

#### Checklist to Policy Conversion
```python
def checklist_to_policy_prompt(self, checklist: Dict) -> str
```
Generates a prompt for converting the structured checklist into SPT (SimplePolicyTalk) DSL format. The SPT format follows:
```
EFFECT Principal "<principal>" Action "<action>" On "<resource>" [When "<condition>"];
```

#### Core Processing Functions

1. `generate_checklist(nl_requirement: str) -> Dict`
   - Takes natural language requirement
   - Uses GPT-4 to generate structured checklist
   - Returns JSON-formatted checklist

2. `generate_policy(checklist: Dict) -> str`
   - Takes structured checklist
   - Uses GPT-4 to generate SPT policy
   - Returns policy statement(s)

3. `generate_test_data(nl_requirement: str, num_iterations: int = 10) -> Dict`
   - Generates multiple policy variations for testing
   - Creates comprehensive test data including:
     - Original requirement
     - Generated checklist
     - Multiple policy variations
     - Metadata about the generation process

4. `run_mvp_test(test_cases: List[str], output_file: str = "policy_test_results.json")`
   - Runs tests on multiple natural language requirements
   - Generates test data for each requirement
   - Saves results to JSON file
   - Provides summary of test results

## Usage Example

```python
# Initialize the engineer
engineer = PolicyRequirementsEngineer()

# Define test cases
test_cases = [
    "Allow the IAM role 'DataAnalyst' to read all objects in the S3 bucket 'analytics-reports' between 9 AM and 5 PM EST on weekdays",
    "Users should be able to manage EC2 instances",
    "Developers can access their own S3 objects in the development environment"
]

# Run tests
engineer.run_mvp_test(test_cases, "policy_test_results.json")
```

## Output Format

The tool generates a JSON file containing:
1. Test run metadata
   - Timestamp
   - Number of test cases
   - Policies per case

2. For each test case:
   - Original natural language requirement
   - Generated checklist with metadata
   - Multiple generated policies
   - Generation metadata

## Checklist Structure

The generated checklist follows this JSON structure:
```json
{
  "checklistMetadata": {
    "version": "1.0",
    "status": "INCOMPLETE|AMBIGUOUS|COMPLETE",
    "totalRequirements": <number>,
    "resolvedRequirements": <number>,
    "ambiguityLevel": "HIGH|MEDIUM|LOW|NONE",
    "validationErrors": [],
    "validationWarnings": []
  },
  "policyIntent": {
    "originalNL": "<original text>",
    "parsedIntent": "<summary>",
    "scope": "SINGLE_RULE|MULTI_RULE|POLICY_SET"
  },
  "requirements": [
    {
      "ruleId": "RULE_001",
      "status": "RESOLVED|AMBIGUOUS|INCOMPLETE",
      "effect": {
        "value": "ALLOW|DENY|UNSPECIFIED",
        "confidence": "EXPLICIT|INFERRED|MISSING",
        "nlSource": "<text from NL>"
      },
      "principal": {
        "type": "SPECIFIC_ARN|ROLE|GROUP|ATTACHED_IDENTITY|UNSPECIFIED",
        "value": "<value or UNSPECIFIED>",
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "resolutionRequired": ["<suggestions>"],
        "nlSource": "<text from NL>"
      },
      "actions": {
        "service": "<service>|UNSPECIFIED",
        "operations": ["<operations>"],
        "pattern": "EXPLICIT_LIST|WILDCARD|PREFIX_PATTERN|UNSPECIFIED",
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "nlSource": "<text from NL>"
      },
      "resources": {
        "type": "SPECIFIC_ARN|PATTERN|WILDCARD|UNSPECIFIED",
        "values": ["<values>"],
        "variables": [],
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "resolutionRequired": ["<suggestions>"],
        "nlSource": "<text from NL>"
      },
      "conditions": {
        "present": true|false,
        "expressions": [],
        "nlSource": "<text from NL>"
      }
    }
  ],
  "resolutionGuidance": {
    "missingRequired": [],
    "ambiguousElements": [],
    "potentialPolicies": <number>,
    "reason": "<explanation>"
  }
}
```

## Dependencies

- openai>=1.0.0: OpenAI API client
- python-dateutil>=2.8.2: Date/time handling
- typing-extensions>=4.0.0: Enhanced type hints
- python-dotenv>=1.0.0: Environment variable management

## Security Notes

- API keys should never be committed to version control
- Always use environment variables for sensitive information
- The `.env` file should be added to `.gitignore` 