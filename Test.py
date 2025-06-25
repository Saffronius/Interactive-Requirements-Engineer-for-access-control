import json
import os
from openai import OpenAI
from typing import List, Dict, Tuple
from datetime import datetime
from dotenv import load_dotenv

class PolicyRequirementsEngineer:
    def __init__(self, api_key: str = None):
        # Load environment variables from .env file
        load_dotenv()
        
        # Use provided api_key or get from environment variable
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or provide it as an argument.")
        
        self.client = OpenAI(api_key=self.api_key)
        
    def _clean_response_text(self, text: str) -> str:
        """Remove markdown code block formatting from response text"""
        text = text.strip()
        
        # Remove opening markdown code block
        if text.startswith('```json'):
            text = text[7:]  # Remove '```json'
        elif text.startswith('```'):
            text = text[3:]   # Remove '```'
        
        # Remove closing markdown code block
        if text.endswith('```'):
            text = text[:-3]  # Remove closing '```'
        
        return text.strip()
        
    def nl_to_checklist_prompt(self, nl_requirement: str) -> str:
        """Generate prompt for converting NL to checklist DSL"""
        return f"""You are an expert in AWS IAM policy requirements analysis. Convert the following natural language requirement into a structured policy requirements checklist.

The checklist must be in the exact JSON format specified below. Analyze the requirement carefully and identify:
1. Whether all required elements are specified
2. Any ambiguities that could lead to multiple interpretations
3. Missing information that prevents unique policy generation

Natural Language Requirement:
"{nl_requirement}"

Output Format:
{{
  "checklistMetadata": {{
    "version": "1.0",
    "status": "INCOMPLETE|AMBIGUOUS|COMPLETE",
    "totalRequirements": <number>,
    "resolvedRequirements": <number>,
    "ambiguityLevel": "HIGH|MEDIUM|LOW|NONE",
    "validationErrors": [],
    "validationWarnings": []
  }},
  "policyIntent": {{
    "originalNL": "<original text>",
    "parsedIntent": "<summary>",
    "scope": "SINGLE_RULE|MULTI_RULE|POLICY_SET"
  }},
  "requirements": [
    {{
      "ruleId": "RULE_001",
      "status": "RESOLVED|AMBIGUOUS|INCOMPLETE",
      "effect": {{
        "value": "ALLOW|DENY|UNSPECIFIED",
        "confidence": "EXPLICIT|INFERRED|MISSING",
        "nlSource": "<text from NL>"
      }},
      "principal": {{
        "type": "SPECIFIC_ARN|ROLE|GROUP|ATTACHED_IDENTITY|UNSPECIFIED",
        "value": "<value or UNSPECIFIED>",
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "resolutionRequired": ["<suggestions>"],
        "nlSource": "<text from NL>"
      }},
      "actions": {{
        "service": "<service>|UNSPECIFIED",
        "operations": ["<operations>"],
        "pattern": "EXPLICIT_LIST|WILDCARD|PREFIX_PATTERN|UNSPECIFIED",
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "nlSource": "<text from NL>"
      }},
      "resources": {{
        "type": "SPECIFIC_ARN|PATTERN|WILDCARD|UNSPECIFIED",
        "values": ["<values>"],
        "variables": [],
        "confidence": "EXPLICIT|INFERRED|AMBIGUOUS|MISSING",
        "ambiguityReason": "<reason if ambiguous>",
        "resolutionRequired": ["<suggestions>"],
        "nlSource": "<text from NL>"
      }},
      "conditions": {{
        "present": true|false,
        "expressions": [],
        "nlSource": "<text from NL>"
      }}
    }}
  ],
  "resolutionGuidance": {{
    "missingRequired": [],
    "ambiguousElements": [],
    "potentialPolicies": <number>,
    "reason": "<explanation>"
  }}
}}

Be extremely careful to identify ALL ambiguities. If status is "COMPLETE", there should be exactly ONE possible policy interpretation.

Output only valid JSON."""

    def checklist_to_policy_prompt(self, checklist: Dict) -> str:
        """Generate prompt for converting checklist to SPT policy"""
        return f"""You are an expert in AWS IAM policy generation using SimplePolicyTalk (SPT) DSL. 
Generate an SPT policy based on the following requirements checklist.

CRITICAL INSTRUCTIONS:
1. You MUST generate a policy that EXACTLY matches the requirements in the checklist
2. If the checklist status is "COMPLETE", generate the unique policy that satisfies all requirements
3. If the checklist has ambiguities, make the SAME interpretation choices consistently
4. Use only the information provided in the checklist - do not add or infer additional requirements

Requirements Checklist:
{json.dumps(checklist, indent=2)}

SPT Syntax Reminder:
- Format: EFFECT Principal "<principal>" Action "<action>" On "<resource>" [When "<condition>"];
- Effects: ALLOW | DENY
- Principal examples: "principal_id:ATTACHED_IDENTITY", "aws_principal_arn:arn:aws:iam::123:role/Name"
- Action examples: "service:s3 action:GetObject", "service:ec2 actions:[\\"StartInstances\\", \\"StopInstances\\"]"
- Resource examples: "resource_pattern:*", "resource_arn:arn:aws:s3:::bucket/*"

Generate ONLY the SPT policy statement(s). Each statement must end with a semicolon.
Output format: Just the SPT statement(s), no explanations or JSON."""

    def generate_checklist(self, nl_requirement: str) -> Dict:
        """Convert NL requirement to checklist using LLM"""
        response = self.client.responses.create(
            model="o4-mini",
            input=self.nl_to_checklist_prompt(nl_requirement),
            reasoning={
                "effort": "high"
            }
        )
        
        # Extract text from response
        try:
            if hasattr(response, 'output_text'):
                raw_text = response.output_text
            elif hasattr(response, 'output') and response.output:
                # Access via output array
                raw_text = response.output[0].content[0].text
            else:
                print("Response object:", response)
                raise ValueError("Unable to extract text from response")
            
            # Clean the response text (remove markdown code blocks)
            cleaned_text = self._clean_response_text(raw_text)
            print("Cleaned JSON:", cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text)
            
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response}")
            raise

    def generate_policy(self, checklist: Dict) -> str:
        """Generate SPT policy from checklist using LLM"""
        response = self.client.responses.create(
            model="o4-mini",
            input=self.checklist_to_policy_prompt(checklist),
            reasoning={
                "effort": "high"
            }
        )
        
        # Extract and clean text from response
        try:
            if hasattr(response, 'output_text'):
                raw_text = response.output_text
            elif hasattr(response, 'output') and response.output:
                raw_text = response.output[0].content[0].text
            else:
                raise ValueError("Unable to extract text from response")
            
            # Clean the response text (remove markdown code blocks if present)
            cleaned_text = self._clean_response_text(raw_text)
            return cleaned_text.strip()
        except Exception as e:
            print(f"Error parsing policy response: {e}")
            print(f"Raw response: {response}")
            raise

    def analyze_requirement_status(self, checklist: Dict) -> Tuple[bool, str, List[str]]:
        """Analyze the checklist status and return feedback if needed"""
        metadata = checklist['checklistMetadata']
        status = metadata['status']
        ambiguity_level = metadata['ambiguityLevel']
        
        if status == "COMPLETE" and ambiguity_level == "NONE":
            return True, "Requirement is complete and unambiguous.", []
        
        feedback_messages = []
        
        # Check for incomplete requirements
        if status == "INCOMPLETE":
            feedback_messages.append("The requirement is incomplete. Missing elements:")
            for req in checklist['requirements']:
                for component in ['effect', 'principal', 'actions', 'resources']:
                    if req[component]['confidence'] == "MISSING":
                        feedback_messages.append(f"- {component.capitalize()}: {req[component].get('nlSource', 'Not specified')}")
        
        # Check for ambiguities
        if ambiguity_level != "NONE":
            feedback_messages.append(f"\nThe requirement has {ambiguity_level.lower()} ambiguity:")
            for req in checklist['requirements']:
                for component in ['principal', 'actions', 'resources']:
                    if req[component]['confidence'] == "AMBIGUOUS":
                        feedback_messages.append(f"- {component.capitalize()}: {req[component]['ambiguityReason']}")
                        if req[component].get('resolutionRequired'):
                            feedback_messages.append(f"  Suggestions: {', '.join(req[component]['resolutionRequired'])}")
        
        # Add resolution guidance if available
        if checklist['resolutionGuidance']['missingRequired'] or checklist['resolutionGuidance']['ambiguousElements']:
            feedback_messages.append("\nResolution guidance:")
            if checklist['resolutionGuidance']['missingRequired']:
                feedback_messages.append("Missing elements that need to be specified:")
                feedback_messages.extend([f"- {item}" for item in checklist['resolutionGuidance']['missingRequired']])
            if checklist['resolutionGuidance']['ambiguousElements']:
                feedback_messages.append("Elements that need clarification:")
                feedback_messages.extend([f"- {item}" for item in checklist['resolutionGuidance']['ambiguousElements']])
        
        return False, "\n".join(feedback_messages), checklist['resolutionGuidance'].get('missingRequired', [])
        
    def process_requirement(self, nl_requirement: str, max_attempts: int = 3) -> Dict:
        """Process a requirement with feedback loop for incomplete/ambiguous cases"""
        attempts = 0
        current_requirement = nl_requirement
        
        while attempts < max_attempts:
            # Generate checklist
            checklist = self.generate_checklist(current_requirement)
            
            # Analyze status
            is_complete, feedback, missing_elements = self.analyze_requirement_status(checklist)
            
            if is_complete:
                return {
                    "status": "success",
                    "checklist": checklist,
                    "policy": self.generate_policy(checklist),
                    "attempts": attempts + 1
                }
            
            # If we've reached max attempts, return the current state
            if attempts == max_attempts - 1:
                return {
                    "status": "incomplete",
                    "checklist": checklist,
                    "feedback": feedback,
                    "missing_elements": missing_elements,
                    "attempts": attempts + 1
                }
            
            # Update requirement based on feedback
            current_requirement = f"""Original requirement: {current_requirement}

Please provide additional information to address the following issues:
{feedback}

Please provide a complete and unambiguous requirement that addresses these points."""
            
            attempts += 1
        
        return {
            "status": "max_attempts_reached",
            "checklist": checklist,
            "feedback": feedback,
            "missing_elements": missing_elements,
            "attempts": attempts
        }

    def run_mvp_test(self, test_cases: List[str], output_file: str = "policy_test_results.json"):
        """Run the MVP test and save results to JSON file"""
        all_results = []
        
        for nl_req in test_cases:
            print(f"\nProcessing: {nl_req[:60]}...")
            result = self.process_requirement(nl_req)
            
            if result["status"] == "success":
                print(f"✓ Successfully generated policy after {result['attempts']} attempts")
            else:
                print(f"✗ Requirement needs clarification:")
                print(result["feedback"])
            
            all_results.append(result)
        
        # Save to JSON file
        with open(output_file, 'w') as f:
            json.dump({
                "test_run": {
                    "timestamp": datetime.now().isoformat(),
                    "total_test_cases": len(test_cases),
                    "policies_per_case": 10
                },
                "results": all_results
            }, f, indent=2)
        
        print(f"\nResults saved to {output_file}")
        print("\nSummary:")
        for i, result in enumerate(all_results):
            print(f"\nTest Case {i + 1}:")
            print(f"  Status: {result['status']}")
            print(f"  Attempts: {result['attempts']}")
            if result["status"] != "success":
                print(f"  Issues: {len(result['missing_elements'])} missing elements")

    def interactive_mode(self):
        """Interactive mode for users to input their own requirements"""
        print("\n" + "="*60)
        print("🔐 Policy Requirements Engineer - Interactive Mode")
        print("="*60)
        print("Enter natural language IAM policy requirements.")
        print("Type 'quit' or 'exit' to stop, 'help' for examples.")
        print("-"*60)
        
        while True:
            try:
                # Get user input
                print("\n💬 Enter your policy requirement:")
                user_input = input("> ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self.show_examples()
                    continue
                elif not user_input:
                    print("❌ Please enter a requirement or type 'help' for examples.")
                    continue
                
                # Process the requirement
                print(f"\n🔄 Processing: {user_input}")
                print("-" * 50)
                
                result = self.process_requirement(user_input)
                
                # Display results
                if result["status"] == "success":
                    print(f"✅ Successfully generated policy after {result['attempts']} attempt(s)!")
                    print("\n📋 Generated SPT Policy:")
                    print("-" * 30)
                    print(result["policy"])
                    print("-" * 30)
                else:
                    print(f"❌ Requirement needs clarification (attempted {result['attempts']} times):")
                    print("\n📝 Feedback:")
                    print(result["feedback"])
                    
                    if result.get("missing_elements"):
                        print(f"\n🔍 Missing {len(result['missing_elements'])} key elements")
                
                # Ask if user wants to save result
                save_choice = input("\n💾 Save this result to file? (y/n): ").strip().lower()
                if save_choice in ['y', 'yes']:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"policy_result_{timestamp}.json"
                    with open(filename, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"✅ Result saved to {filename}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again or type 'help' for examples.")
    
    def show_examples(self):
        """Show example policy requirements"""
        examples = [
            "Allow the IAM role 'DataAnalyst' to read all objects in the S3 bucket 'analytics-reports' between 9 AM and 5 PM EST on weekdays",
            "Allow the IAM role 'JohnDoe' in account 111122223333 to get objects and object versions from the S3 bucket 'amzn-s3-demo-bucket' only for objects tagged with environment=production",
            "Grant the IAM group 'Developers' permission to start and stop EC2 instances in the us-west-2 region",
            "Allow users with the tag Department=Finance to access CloudWatch metrics for billing",
            "Deny all users access to delete S3 objects in the 'critical-backups' bucket"
        ]
        
        print("\n📚 Example Policy Requirements:")
        print("-" * 40)
        for i, example in enumerate(examples, 1):
            print(f"{i}. {example}")
        print("-" * 40)

# Example usage
if __name__ == "__main__":
    # Initialize the engineer
    engineer = PolicyRequirementsEngineer()
    ß
    # Check if user wants interactive mode
    print("Policy Requirements Engineer")
    print("1. Run predefined test cases")
    print("2. Interactive mode - enter your own requirements")
    
    choice = input("\nSelect mode (1 or 2): ").strip()
    
    if choice == "2":
        engineer.interactive_mode()
    else:
        # Test cases
        test_cases = [
            # AWS Documentation Example - should be considered complete
            "Allow the IAM role 'JohnDoe' in account 111122223333 to get objects and object versions from the S3 bucket 'amzn-s3-demo-bucket' only for objects tagged with environment=production"
        ]
        
        # Run tests
        engineer.run_mvp_test(test_cases, "policy_test_results.json")