from llama_cpp import Llama
from functionary.prompt_template import get_prompt_template_from_tokenizer
from transformers import AutoTokenizer
import json
import sys
import pprint
import handlers
from datetime import date
from datetime import datetime

pp = pprint.PrettyPrinter(indent=2)


class Assistant:
    def __init__(self, init_context):
        json_text = open("functions.json", "r").read()

        self.functions = json.loads(json_text)

        self.llm = Llama(model_path="models/functionary-small-v2.2.q4_0.gguf",
                         n_ctx=4096, n_gpu_layers=35, verbose=True)

        self.tokenizer = AutoTokenizer.from_pretrained(
            "meetkai/functionary-small-v2.2-GGUF", legacy=True)

        self.prompt_template = get_prompt_template_from_tokenizer(
            self.tokenizer)

        self.function_calls = {}
        self.init_context = init_context
        self.init()

    def init(self):
        self.messages = self.init_context.copy()

    def run_inference(self):
        all_messages = list(self.messages) + [{"role": "assistant"}]

        prompt_str = self.prompt_template.get_prompt_from_messages(
            all_messages, self.functions)
        token_ids = self.tokenizer.encode(prompt_str)

        gen_tokens = []

        # Get list of stop_tokens
        stop_token_ids = [self.tokenizer.encode(
            token)[-1] for token in self.prompt_template.get_stop_tokens_for_generation()]
        print("stop_token_ids: ", stop_token_ids)

        # We use function generate (instead of __call__) so we can pass in list of token_ids
        for token_id in self.llm.generate(token_ids, temp=0):
            if token_id in stop_token_ids:
                break
            gen_tokens.append(token_id)

        llm_output = self.tokenizer.decode(gen_tokens)
        result = self.prompt_template.parse_assistant_response(llm_output)

        print(result)

        return result

    def confirm(self, func_id, data = ""):
        func_call = self.function_calls[func_id]
        func_name = func_call["function"]["name"]
        func_param = func_call["function"]["arguments"]

        result = None

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
            case 'add_activities':
                result = handlers.add_activities(func_param)
            case 'get_project_activities':
                result = handlers.get_project_activities(func_param)
            case 'add_absence':
                result = handlers.add_absence(func_param)
            case 'prompt_date':
                result = data

        self.messages.append(
            {"role": "tool", "tool_call_id": func_id, "name": func_name, "content": result})

        del self.function_calls[func_id]

    def generate_message(self, send_client_callback, user_input=None):
        if user_input is not None:
            self.messages.append({"role": "user", "content": user_input})

        pp.pprint(self.messages)

        inference = self.run_inference()

        self.messages.append(inference)

        tool_calls = inference["tool_calls"]

        for tool_call in tool_calls:
            tool_id = tool_call["id"]
            self.function_calls[tool_id] = tool_call
            func_name = tool_call["function"]["name"]

            # Auto validate all get functions
            if "get" in func_name:
                print("Autovalidating message")
                self.confirm(tool_id)
                self.generate_message(send_client_callback)
            else:
                print("Message needs validation")
                send_client_callback({"role": "system-confirm", "content": inference["content"], "function": tool_call["function"], "tool_id": tool_id})

        if not tool_calls:
            print("No tool calls", inference)
            send_client_callback(inference)
