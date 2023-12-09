from llama_cpp import Llama
from functionary.prompt_template import get_prompt_template_from_tokenizer
from transformers import AutoTokenizer
import json
import sys
import pprint
pp = pprint.PrettyPrinter(indent=2)

json_text = open("functions.json", "r").read()
 
functions = json.loads(json_text)

# You can download gguf files from https://huggingface.co/meetkai/functionary-7b-v1.4-GGUF/tree/main
llm = Llama(model_path="models/functionary-7b-v1.4.q4_0.gguf", n_ctx=4096, n_gpu_layers=-35, verbose=True)
messages = [
    {"role": "system", "content": "Current date is 2023-12-04."},
    {"role": "system", "content": "Currently connected user is aleksandar@company.com"},
    {"role": "user", "content": str(sys.argv[1])}
]

# Create tokenizer from HF. 
# We found that the tokenizer from llama_cpp is not compatible with tokenizer from HF that we trained
# The reason might be we added new tokens to the original tokenizer
# So we will use tokenizer from HuggingFace
tokenizer = AutoTokenizer.from_pretrained("meetkai/functionary-7b-v1.4", legacy=True)

# prompt_template will be used for creating the prompt
prompt_template = get_prompt_template_from_tokenizer(tokenizer)

# Before inference, we need to add an empty assistant (message without content or function_call)
messages.append({"role": "assistant"})

# Create the prompt to use for inference
while(True):
    print("Sending prompt")
    pp.pprint(messages)

    prompt_str = prompt_template.get_prompt_from_messages(messages, functions)
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

    # parse the message from llm_output
    result = prompt_template.parse_assistant_response(llm_output)

    print(result)
    messages.append(result)

    if "function_call" in result:
        f_name = input("function name: ")
        f_result = input("function return :")
        messages.append({"role": "function", "name": f_name, "content": f_result})
    else:
        user_input = input("user: ")
        messages.append({"role": "user", "content": user_input})

    messages.append({"role": "assistant"})

