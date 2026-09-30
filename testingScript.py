import csv
import requests
from idGen import generate_ids
from conversation import Conversation
from prompt_generator import generate_prompt, load_prompt_templates
from drain_responses import drain_cognigy_responses


ENDPOINT_URL = "SECRET"
ENDPOINT_CHAT_URL = "SECRET"
OPENAI_API = "f4c12e6ae1fb4b6bb29959314d32807d"
DEV_INSTRUCTION = "You are a customer of an energy company. You are NOT a support agent, company representative or assistant. Never break character and always speak from a customer perspective. You are not an energy company representative."
DUMMY_CSV_PATH = "dummy.csv"
PROMPTS_PATH = "prompts.csv"
USE_CASE = "Submit Meter Reading"  # e.g. "Submit Meter Reading" to limit runs to a single use case


def build_chat_context(dummy_id: int, use_case: str, prompt_template: str) -> str:
    """
    Inject dummy-specific context into a single use-case prompt template.
    Keeps DEV_INSTRUCTION fixed while swapping placeholders with customer data.
    """
    prompt = generate_prompt(
        path_prompt=PROMPTS_PATH,
        use_case=use_case,
        file_path_dummy=DUMMY_CSV_PATH,
        dummy_id=dummy_id,
        prompt_template=prompt_template
    )
    return f"{DEV_INSTRUCTION} {prompt}"


def load_dummy_data(file_path: str):
    """
    Load dummy.csv once and return both the ID ordering and row lookup map.
    Prevents repeated disk reads while preserving the order in the CSV.
    """
    dummy_ids = []
    dummy_records = {}
    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        id_field = reader.fieldnames[0] if reader.fieldnames else "id"
        for row in reader:
            raw_value = row.get(id_field)
            if raw_value is None:
                continue
            try:
                row_id = int(raw_value)
            except ValueError:
                continue
            dummy_ids.append(row_id)
            dummy_records[row_id] = row
    return dummy_ids, dummy_records

class CognigyTester:
    
    def __init__(self, endpoint_url, user_id=None, session_id=None):
        """Store the endpoint URL plus stable user/session IDs for this run."""
        self.endpoint_url = endpoint_url
        # Generate IDs once per run
        self.user_id, self.session_id = (user_id, session_id) if user_id and session_id else generate_ids()
        # Keep initial IDs for runtime consistency checks
        self._initial_user_id = self.user_id
        self._initial_session_id = self.session_id
        # Log the IDs used for this run
        print(f"Initialized CognigyTester with user_id={self.user_id}, session_id={self.session_id}")


    
    def send_to_cognigy(self, message):
        """Post a user utterance to Cognigy and aggregate all bot texts."""
        if (self.user_id != getattr(self, "_initial_user_id", None)) or (self.session_id != getattr(self, "_initial_session_id", None)):
            print(f"Warning: user/session ID changed during run. initial=({self._initial_user_id},{self._initial_session_id}) current=({self.user_id},{self.session_id})")

        payload = {
            "userId": self.user_id,
            "sessionId": self.session_id,
            "text": message
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            bot_texts = []

            output_stack = data.get("outputStack", [])
            for entry in output_stack:
                text = entry.get("text")
                source = entry.get("source")
                if text and (not source or source == "bot"):
                    bot_texts.append(text)

            # Include top-level text if it’s not a duplicate
            top_text = data.get("text")
            if top_text and top_text.strip() not in " ".join(bot_texts):
                bot_texts.append(top_text)

            full_response = " ".join(bot_texts).strip()
            if full_response:
                print(f"Cognigy: '{full_response}'")

            return full_response

        except requests.exceptions.RequestException as e:
            print(f"Error sending to Cognigy: {e}")
            return ""


    def send_to_chatgpt(self, message: str, conversation: Conversation):
        """Send the full conversation history to Azure OpenAI and return ChatGPT's reply."""
        headers = {
            "api-key": OPENAI_API,
            "Content-Type": "application/json"
        }
        
        # Build the messages array with full conversation history
        messages = [
            # Start with the system prompt
            {"role": "system", "content": conversation.initial_prompt_to_chatgpt}
        ]
        
        # Add all previous exchanges with proper roles
        for resp in conversation.ai_responses:
            if resp.ai_name == "ChatGPT":
                messages.append({"role": "assistant", "content": resp.response})
            elif resp.ai_name == "Cognigy":
                messages.append({"role": "user", "content": resp.response})
                
        # Add the current message
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "gpt-4.1-mini",
            "messages": messages
        }
        try:
            response = requests.post(ENDPOINT_CHAT_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            bot_message = data["choices"][0]["message"]["content"].strip()
            print(f"ChatGPT: '{bot_message}'")
            return bot_message

        except requests.exceptions.RequestException as e:
            print(f"Error sending to ChatGPT: {e}")
            return ""


def run_conversation_for_prompt(
    dummy_id: int,
    customer_record: dict,
    use_case: str,
    prompt_template: str,
    prompt_index: int,
    testcase_ID: str | None = None
) -> None:
    """
    Run the full Cognigy ↔ ChatGPT turn-taking loop for one dummy + prompt.
    Handles metadata capture (testcase_ID, phone number) and persistence.
    """
    try:
        chat_context = build_chat_context(dummy_id, use_case, prompt_template)
    except ValueError as exc:
        print(f"Skipping dummy {dummy_id} for use case '{use_case}': {exc}")
        return

    testcase_label = testcase_ID or f"{use_case}__prompt_{prompt_index}"
    phone_number = (
        customer_record.get("phone_number") or customer_record.get("phone")
    )
    if not phone_number:
        raise ValueError(f"Dummy {dummy_id} missing phone number in {DUMMY_CSV_PATH}")
    phone_number = phone_number.strip()

    print(f"\n=== {use_case} | prompt #{prompt_index} | dummy {dummy_id} ===")
    print(f"The prompt is: {chat_context}")

    user_id, session_id = generate_ids()
    print(f"Conversation started with IDs: {user_id}, {session_id}\n")

    conversation = Conversation(
        initial_prompt_to_chatgpt=chat_context,
        session_id=session_id,
        customer_phone_number=phone_number,
        testcase_ID=testcase_label
    )

    tester = CognigyTester(ENDPOINT_URL, user_id, session_id)

    cognigy_replies = drain_cognigy_responses(".", tester)
    if cognigy_replies:
        conversation.add_response("Cognigy", " ".join(cognigy_replies), ".")

    for _ in range(40):
        if not cognigy_replies:
            print("\nCognigy stopped responding")
            break

        full_cognigy_message = " ".join(cognigy_replies)
        chatgpt_reply = tester.send_to_chatgpt(full_cognigy_message, conversation)
        if chatgpt_reply:
            conversation.add_response("ChatGPT", chatgpt_reply, full_cognigy_message)
        else:
            print("\nChatGPT stopped responding")
            break

        cognigy_replies = drain_cognigy_responses(chatgpt_reply, tester)
        if cognigy_replies:
            conversation.add_response("Cognigy", " ".join(cognigy_replies), chatgpt_reply)

    conversation.print_history()
    conversation.save_to_json()


if __name__ == "__main__":
    prompt_templates = load_prompt_templates(PROMPTS_PATH)
    dummy_ids, dummy_records = load_dummy_data(DUMMY_CSV_PATH)

    if not prompt_templates:
        print("No prompts found—nothing to run.")
    elif not dummy_ids:
        print("No dummy IDs found—nothing to run.")
    else:
        # Optional filter: allow the user to run only a single use case block.
        if USE_CASE:
            selected_templates = prompt_templates.get(USE_CASE)
            if not selected_templates:
                print(f"Use case '{USE_CASE}' not found—nothing to run.")
                exit(0)
            prompt_templates = {USE_CASE: selected_templates}

        # Iterate use case → prompt variant → dummy row and run the full test loop.
        for use_case, templates in prompt_templates.items():
            for idx, template in enumerate(templates, start=1):
                for dummy_id in dummy_ids:
                    testcase_label = f"{use_case}__prompt_{idx}"
                    record = dummy_records.get(dummy_id)
                    if not record:
                        print(f"Skipping missing dummy {dummy_id}")
                        continue
                    run_conversation_for_prompt(
                        dummy_id,
                        record,
                        use_case,
                        template,
                        idx,
                        testcase_ID=testcase_label
                    )
