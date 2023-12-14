from llama_cpp import Llama
from functionary.prompt_template import get_prompt_template_from_tokenizer
from transformers import AutoTokenizer
import json
import sys
import pprint
import handlers
from datetime import date

pp = pprint.PrettyPrinter(indent=2)


class Assistant:
    def __init__(self):
        json_text = open("functions.json", "r").read()

        self.functions = json.loads(json_text)

        self.llm = Llama(model_path="models/functionary-7b-v1.4.q4_0.gguf",
                         n_ctx=4096, n_gpu_layers=35, verbose=True)
        self.messages = [
            {"role": "system", "content": "Client stdout is HTML capable"},
            {"role": "system", "content": f'Current date is: {date.today()}'},
            {"role": "system", "content": 'Locale is en-GB'},
            {"role": "system",
                "content": "Currently connected user is 'aleksandar@company.com' Firstname Aleksandar Lastname KIRILOV"},
            {"role": "system", "content": "This program helps user fill in their monthly activity reports. Each activity "
                                          "report is associated to a project that user has worked on. Activities can be "
                                          "reported in increments of 25% per day. A single day cannot have more than 100% of "
                                          "reported time - this includes activities and absences."},
        ]

        self.tokenizer = AutoTokenizer.from_pretrained(
            "meetkai/functionary-7b-v1.4", legacy=True)

        self.prompt_template = get_prompt_template_from_tokenizer(
            self.tokenizer)


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

    def confirm(self):
        func_name = self.function_call["function_call"]["name"]
        func_param = self.function_call["function_call"]["arguments"]

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
            case 'get_dates_of_week':
                result = handlers.get_dates_of_week(func_param)

        self.messages.append(
            {"role": "function", "name": func_name, "content": result})


    def generate_message(self, user_input=None):
        if user_input is not None:
            self.messages.append({"role": "user", "content": user_input})

        pp.pprint(self.messages)

        inference = self.run_inference()

        self.messages.append(inference)

        if "function_call" in inference:
            self.function_call = inference
            func_name = self.function_call["function_call"]["name"]

            # Auto validate all get functions
            if "get" in func_name:
                print("Autovalidating message")
                self.confirm()
                return self.generate_message()

            return {"role": "system-confirm", "content": inference}
        else:
            return inference
