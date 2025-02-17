import sys
import json

from colorama import Fore, Style
from litellm import completion, token_counter

from dir_assistant.assistant.git_assistant import GitAssistant


class LiteLLMAssistant(GitAssistant):
    def __init__(
        self,
        lite_llm_model,
        lite_llm_model_uses_system_message,
        lite_llm_context_size,
        lite_llm_pass_through_context_size,
        system_instructions,
        embed,
        index,
        chunks,
        context_file_ratio,
        output_acceptance_retries,
        use_cgrag,
        print_cgrag,
        commit_to_git,
    ):
        super().__init__(
            system_instructions,
            embed,
            index,
            chunks,
            context_file_ratio,
            output_acceptance_retries,
            use_cgrag,
            print_cgrag,
            commit_to_git,
        )
        self.lite_llm_model = lite_llm_model
        self.context_size = lite_llm_context_size
        self.pass_through_context_size = lite_llm_pass_through_context_size
        self.lite_llm_model_uses_system_message = lite_llm_model_uses_system_message
        print(
            f"{Fore.LIGHTBLACK_EX}LiteLLM context size: {self.context_size}{Style.RESET_ALL}"
        )

    def initialize_history(self):
        super().initialize_history()
        if not self.lite_llm_model_uses_system_message:
            self.chat_history[0]["role"] = "user"

    def call_completion(self, chat_history):
        if self.pass_through_context_size:
            return completion(
                model=self.lite_llm_model,
                messages=chat_history,
                stream=True,
                timeout=600,
                num_ctx=self.context_size,
            )
        else:
            llm_response = completion(
                # model=self.lite_llm_model,
                # model='deepseek/deepseek-reasoner',
                model='azure/o1-mini',
                api_base = "https://hkelectric-openai00.openai.azure.com/",
                api_version = "2024-08-01-preview",
                messages=chat_history,
                stream=False,
                timeout=60000,
                #max_tokens=128000,
            )
            return llm_response

    def run_completion_generator(
        self, completion_output, output_message, write_to_stdout
    ):
        # for chunk in completion_output:
        #     delta = chunk["choices"][0]["delta"]
        #     if "content" in delta and delta["content"] != None:
        #         output_message["content"] += delta["content"]
        #         if write_to_stdout:
        #             sys.stdout.write(delta["content"])
        #             sys.stdout.flush()
        #         else:
        #             sys.stdout.write('.')
        #             sys.stdout.flush()

        output_message["content"] += completion_output.choices[0].message.content
        if write_to_stdout:
            sys.stdout.write(completion_output.choices[0].message.content)
            sys.stdout.flush()

        if not output_message["content"]:
            raise ValueError("LLM reply was blank!")
            # sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
            # sys.stdout.write(
            #     Style.BRIGHT + Fore.GREEN + f"\r!!!LLM reply was blank!!!\n" + Style.RESET_ALL
            # )
            # sys.stdout.flush()
        return output_message

    def count_tokens(self, text):
        return token_counter(
            model=self.lite_llm_model, messages=[{"user": "role", "content": text}]
        )
    
    def call_completion_fc(self, user_input, relevant_full_text, outfile):
        # Add the user input to the chat history
        user_content = relevant_full_text + user_input
        self.add_user_history(user_content, user_input)
        # Remove old messages from the chat history if too large for context
        self.cull_history()
        # call LLM with function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "output_file",
                    "description": "output program code to file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {
                                "type": "string",
                                "description": "path name of the file to write to",
                            },
                            "program_code": {
                                "type": "string",
                                "description": "program code to write to the file",
                            },
                        },
                        "required": ["file_name", "program_code"],
                    },
                },
            }
        ]
        response = completion(
                model='azure/o1-mini',
                api_base = "https://hkelectric-openai00.openai.azure.com/",
                api_version = "2024-08-01-preview",
                messages=self.chat_history,
                stream=False,
                timeout=60000,
                tools=tools,
            )
        response_message = response.choices[0].message
        tool_calls = response.choices[0].message.tool_calls
        for tool_call in tool_calls:
            if tool_call.function.name == "output_file":
                tool_call_data = json.loads(tool_call.function.arguments)
                file_name = tool_call_data["file_name"].replace('\\\\', '\\')
                if file_name == outfile:
                    program_code = tool_call_data["program_code"].replace('\\n', '\n').replace('\\"', '\"')
                    self.output_file(file_name, program_code)
        return

    def output_file(self, file_name, program_code):
        with open(file_name, "w") as file:
            file.write(program_code)

    # enable selection of R1 LLM per API call
    def call_completion_r1(self, chat_history):
        llm_response = completion(
            # model=self.lite_llm_model,
            model='deepseek/deepseek-reasoner',
            # model='azure/o1-mini',
            # api_base = "https://hkelectric-openai00.openai.azure.com/",
            # api_version = "2024-08-01-preview",
            messages=chat_history,
            stream=False,
            timeout=120000,
            #max_tokens=128000,
        )
        return llm_response
