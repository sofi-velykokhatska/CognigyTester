import time

def drain_cognigy_responses(initial_message, tester, wait_seconds=0.5):
    """
    Sends a single message to Cognigy and waits briefly to ensure the full response is returned.
    Does NOT send empty messages (avoids 400 errors).
    """
    all_messages = []

    # Send user input once
    response = tester.send_to_cognigy(initial_message)

    if response:
        all_messages.append(response)

    # Give Cognigy time to complete response stack (if delayed in same payload)
    time.sleep(wait_seconds)

    return all_messages
