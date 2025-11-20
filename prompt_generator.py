from collections import OrderedDict
from typing import Dict, List, Optional

import pandas as pd

_PROMPT_CACHE: Dict[str, "OrderedDict[str, List[str]]"] = {}


def load_prompt_templates(path_prompt: str) -> "OrderedDict[str, List[str]]":
    """Parse prompts.csv into an ordered mapping of use_case -> list of prompt templates."""
    if path_prompt in _PROMPT_CACHE:
        return _PROMPT_CACHE[path_prompt]

    prompts_by_case: "OrderedDict[str, List[str]]" = OrderedDict()
    current_case: Optional[str] = None
    current_lines: List[str] = []

    def commit_prompt():
        nonlocal current_lines
        if current_case and current_lines:
            text = "\n".join(line for line in current_lines if line).strip()
            if text:
                prompts_by_case.setdefault(current_case, []).append(text)
        current_lines = []

    with open(path_prompt, encoding="utf-8-sig") as csvfile:
        for raw_line in csvfile:
            line = raw_line.strip("\n")
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("use_case"):
                continue
            if set(stripped) <= {",", '"'}:
                continue

            if ";" in stripped:
                before, after = stripped.split(";", 1)
                new_case = before.strip().strip('"')
                prompt_start = after.strip().strip('"')

                if new_case:
                    commit_prompt()
                    current_case = new_case
                elif current_case:
                    commit_prompt()
                else:
                    continue

                current_lines = []
                if prompt_start:
                    current_lines.append(prompt_start.rstrip(","))
                continue

            cleaned_line = stripped.strip('"').rstrip(",")
            if cleaned_line:
                current_lines.append(cleaned_line)

    commit_prompt()
    _PROMPT_CACHE[path_prompt] = prompts_by_case
    return prompts_by_case


def generate_prompt(
    path_prompt: str,
    use_case: str,
    file_path_dummy: str,
    dummy_id: int,
    prompt_template: Optional[str] = None
) -> str:
    """
    Generate a prompt string by combining a template from prompts.csv with customer data from dummy.csv
    
    Args:
        path_prompt: Path to the prompts CSV file containing use case templates
        use_case: Name of the use case to look up in prompts.csv
        file_path_dummy: Path to the dummy CSV file containing customer data
        dummy_id: ID of the customer in dummy.csv
        prompt_template: Optional explicit prompt template to use. If omitted, the first template of the use case is used.
        
    Returns:
        str: The filled-in prompt with customer data
        
    Raises: 
        ValueError: If use case or dummy_id not found, or if files cannot be read
    """
    try:
        if prompt_template is None:
            prompts_by_case = load_prompt_templates(path_prompt)
            templates = prompts_by_case.get(use_case)
            if not templates:
                raise ValueError(f"Use case '{use_case}' not found in {path_prompt}")
            prompt_template = templates[0]

        dummy_df = pd.read_csv(file_path_dummy, sep=';')
        customer_row = dummy_df[dummy_df['id'] == dummy_id]
        if customer_row.empty:
            raise ValueError(f"Customer ID {dummy_id} not found in {file_path_dummy}")

        customer_data = customer_row.iloc[0]
        replacements = {
            '<full_name>': customer_data.get('full_name') if 'full_name' in customer_data.index else customer_data.get('name'),
            '<phone_number>': customer_data.get('phone_number') if 'phone_number' in customer_data.index else customer_data.get('phone'),
            '<email>': customer_data.get('email'),
            '<zipcode>': str(customer_data.get('zipcode')) if 'zipcode' in customer_data.index else str(customer_data.get('postal')),
            '<iban_last3>': str(customer_data.get('iban_last3')),
            '<date_of_birth>': customer_data.get('birthday') if 'birthday' in customer_data.index else customer_data.get('date_of_birth'),
            '<meter_id>': str(customer_data.get('meter_id')),
            '<meter_value>': str(customer_data.get('new_meter_value')) if 'new_meter_value' in customer_data.index else str(customer_data.get('meter_value')),
            '<street_address>': customer_data.get('street_address'),
            '<city>': customer_data.get('city')
        }

        filled_prompt = prompt_template
        for placeholder, value in replacements.items():
            if pd.notna(value):
                filled_prompt = filled_prompt.replace(placeholder, str(value))

        return filled_prompt
        
    except FileNotFoundError as e:
        raise ValueError(f"Could not find file: {e.filename}")
    except pd.errors.EmptyDataError:
        raise ValueError("One of the CSV files is empty")
    except Exception as e:
        raise ValueError(f"Error processing files: {str(e)}")
