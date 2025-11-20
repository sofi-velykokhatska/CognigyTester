from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Literal, Optional
import json
import csv
import os

@dataclass
class AiResponse:
    """Represents a single response in the AI conversation"""
    ai_name: str
    response: str
    received_date: datetime
    prompt: str

@dataclass
class Conversation:
    """Tracks the full conversation between AIs"""
    initial_prompt_to_chatgpt: str
    session_id: str
    customer_phone_number: str = ""
    testcase_ID: Optional[str] = None
    ai_responses: List[AiResponse] = field(default_factory=list)

    def add_response(self, ai_name: str, response: str, prompt: str) -> None:
        """Add a new response to the conversation history"""
        self.ai_responses.append(
            AiResponse(
                ai_name=ai_name,
                response=response,
                received_date=datetime.now(),
                prompt=prompt
            )
        )
    
    def print_history(self) -> None:
        """Print the full conversation history with timestamps"""
        print("\nConversation History:")
        print(f"Session ID: {self.session_id}")
        if self.testcase_ID:
            print(f"Test Case: {self.testcase_ID}")
        print(f"Customer Phone: {self.customer_phone_number}")
        print(f"Initial ChatGPT Prompt: {self.initial_prompt_to_chatgpt}")
        print("\nResponses:")
        for resp in self.ai_responses:
            print(f"\n{resp.received_date.strftime('%H:%M:%S')} - {resp.ai_name}")
            print(f"Prompt: {resp.prompt}")
            print(f"Response: {resp.response}")
            
    def save_to_json(self, directory: str = "conversations") -> str:
        """Save the conversation to a JSON file in the specified directory
        
        Args:
            directory: Where to save the conversation files (default: 'conversations')
            
        Returns:
            The path to the saved file
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Generate filename with session_id and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{self.session_id}_{timestamp}.json"
        filepath = os.path.join(directory, filename)
        
        # Convert conversation to dict, handling datetime serialization
        conversation_dict = {
            "session_id": self.session_id,
            "initial_prompt_to_chatgpt": self.initial_prompt_to_chatgpt,
            "customer_phone_number": self.customer_phone_number,
            "testcase_ID": self.testcase_ID,
            "responses": [{
                "ai_name": resp.ai_name,
                "response": resp.response,
                "received_date": resp.received_date.isoformat(),
                "prompt": resp.prompt
            } for resp in self.ai_responses]
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_dict, f, indent=2, ensure_ascii=False)
            
        print(f"\nConversation saved to: {filepath}")
        return filepath
