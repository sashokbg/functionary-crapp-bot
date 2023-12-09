from llama_cpp import Llama
from functionary.prompt_template import get_prompt_template_from_tokenizer
from transformers import AutoTokenizer
import json
import sys
import pprint
import handlers
from datetime import date

pp = pprint.PrettyPrinter(indent=2)

json_text = open("functions.json", "r").read()

functions = json.loads(json_text)

# You can download gguf files from https://huggingface.co/meetkai/functionary-7b-v1.4-GGUF/tree/main
llm = Llama(model_path="models/functionary-7b-v2.q4_0.gguf", n_ctx=4096, n_gpu_layers=35, verbose=False)
messages = [
    {"role": "system", "content": "Environment is Python3"},
    {"role": "system", "content": f'Current date is: {date.today()}'},
    {"role": "system", "content": "Currently connected user is 'aleksandar@company.com'"},
    {"role": "system", "content": "This program helps user fill in their monthly activity reports. Each activity "
                                  "report is associated to a project that user has worked on. Activities can be "
                                  "reported in increments of 25% per day. A single day cannot have more than 100% of "
                                  "reported time"},
    {"role": "user", "content": str(sys.argv[1])}
]

# Create tokenizer from HF.
# We found that the tokenizer from llama_cpp is not compatible with tokenizer from HF that we trained
# The reason might be we added new tokens to the original tokenizer
# So we will use tokenizer from HuggingFace
tokenizer = AutoTokenizer.from_pretrained("meetkai/functionary-7b-v2", legacy=True)

# prompt_template will be used for creating the prompt
prompt_template = get_prompt_template_from_tokenizer(tokenizer)


def generate_message(messages, functions):
    # Before inference, we will add an empty message with role=assistant
    all_messages = list(messages) + [{"role": "assistant"}]

    # pp.pprint(all_messages)

    # Create the prompt to use for inference
    prompt_str = prompt_template.get_prompt_from_messages(all_messages, functions)
    token_ids = tokenizer.encode(prompt_str)

    gen_tokens = []
    # Get list of stop_tokens
    stop_token_ids = [tokenizer.encode(token)[-1] for token in prompt_template.get_stop_tokens_for_generation()]
    print("stop_token_ids: ", stop_token_ids)

    # We use function generate (instead of __call__) so we can pass in list of token_ids
    for token_id in llm.generate(token_ids, temp=0):
        if token_id in stop_token_ids:
            break
        gen_tokens.append(token_id)

    llm_output = tokenizer.decode(gen_tokens)
    result = prompt_template.parse_assistant_response(llm_output)
    return result


while True:
    print("******* NEXT PROMPT **********\n\n")

    result = generate_message(messages, functions)

    print(result)
    messages.append(result)

    tool_calls = result['tool_calls']

    if tool_calls:
        tool_call = tool_calls[0]

        func_name = tool_call["function"]["name"]
        func_param = tool_call["function"]["arguments"]

        match func_name:
            case 'get_all_projects':
                result = handlers.get_all_projects()
            case 'get_projects_for_user':
                result = handlers.get_projects_for_user(func_param)
            case 'create_project':
                result = handlers.create_project(func_param)
            case 'get_all_employees':
                result = handlers.get_all_employees()
            case 'add_employee':
                result = handlers.add_employee(func_param)
            case 'assign_project_to_employee':
                result = handlers.assign_project_to_employee(func_param)

        messages.append({
            "tool_call_id": tool_call["id"],
            "role": "tool",
            "name": func_name,
            "content": result,
        });
        # messages.append({"role": "assistant", "name": func_name, "content": result})
    else:
        user_input = input("user: ")
        messages.append({"role": "user", "content": user_input})

