import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

class BedrockClient:
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        # Amazon Nova Pro model
        self.model_id = "amazon.nova-pro-v1:0"

    def invoke(self, messages: list, system_prompt: str = "") -> str:
        """
        Call Amazon Nova via Bedrock
        messages = [{"role": "user", "content": "..."}, ...]
        """
        try:
            body = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": 4096,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            }

            # Add system prompt if provided
            if system_prompt:
                body["system"] = [
                    {
                        "text": system_prompt
                    }
                ]

            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )

            response_body = json.loads(response["body"].read())
            return response_body["output"]["message"]["content"][0]["text"]

        except Exception as e:
            return f"❌ Bedrock Error: {str(e)}"

    def stream_invoke(self, messages: list, system_prompt: str = ""):
        """
        Streaming response from Nova
        Yields text chunks
        """
        try:
            body = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": 4096,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            }

            if system_prompt:
                body["system"] = [{"text": system_prompt}]

            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )

            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield delta.get("text", "")

        except Exception as e:
            yield f"❌ Streaming Error: {str(e)}"