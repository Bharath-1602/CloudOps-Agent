import json
from agent.bedrock_client import BedrockClient
from agent.prompts import (
    SYSTEM_PROMPT,
    SCAN_ANALYSIS_PROMPT,
    CHAT_PROMPT,
    QUICK_FIX_PROMPT
)


class CloudOpsAgent:
    def __init__(self):
        self.bedrock = BedrockClient()
        self.scan_results = None
        self.conversation_history = []

    def analyze_scan(self, scan_data: dict) -> str:
        """
        Send scan results to Nova for analysis
        """
        self.scan_results = scan_data

        # Convert scan data to readable string
        scan_str = json.dumps(scan_data, indent=2, default=str)

        prompt = SCAN_ANALYSIS_PROMPT.format(scan_data=scan_str)

        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        response = self.bedrock.invoke(
            messages=messages,
            system_prompt=SYSTEM_PROMPT
        )

        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": [{"text": "Please analyze my AWS scan results"}]
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": [{"text": response}]
        })

        return response

    def chat(self, user_message: str) -> str:
        """
        Chat with agent about cloud resources
        """
        # Build context from scan results
        scan_context = ""
        if self.scan_results:
            scan_context = json.dumps(self.scan_results, indent=2, default=str)
        else:
            scan_context = "No scan has been performed yet. Ask user to scan first."

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": [{"text": user_message}]
        })

        # Build messages with context
        system = CHAT_PROMPT.format(scan_context=scan_context[:8000])

        # Keep last 10 messages to avoid token limits
        recent_history = self.conversation_history[-10:]

        response = self.bedrock.invoke(
            messages=recent_history,
            system_prompt=SYSTEM_PROMPT + "\n\n" + system
        )

        # Add response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": [{"text": response}]
        })

        return response

    def get_quick_fix(self, resource: str, problem: str) -> str:
        """
        Get a specific fix for a resource problem
        """
        prompt = QUICK_FIX_PROMPT.format(
            resource=resource,
            problem=problem
        )

        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        return self.bedrock.invoke(
            messages=messages,
            system_prompt=SYSTEM_PROMPT
        )

    def clear_history(self):
        self.conversation_history = []
        self.scan_results = None