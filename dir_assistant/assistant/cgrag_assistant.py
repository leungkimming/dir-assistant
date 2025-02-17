import copy
import sys
import json

from colorama import Fore, Style

from dir_assistant.assistant.base_assistant import BaseAssistant
from prompt_toolkit import prompt as ask_prompt

class CGRAGAssistant(BaseAssistant):
    def __init__(
        self,
        system_instructions,
        embed,
        index,
        chunks,
        context_file_ratio,
        output_acceptance_retries,
        use_cgrag,
        print_cgrag,
    ):
        super().__init__(
            system_instructions,
            embed,
            index,
            chunks,
            context_file_ratio,
            output_acceptance_retries,
        )
        self.use_cgrag = use_cgrag
        self.print_cgrag = print_cgrag

    def write_assistant_thinking_message(self):
        # Disable CGRAG if the fileset is smaller than 4x the LLM context
        # total_tokens = sum(chunk['tokens'] for chunk in self.chunks)

        # Display the assistant thinking message
        if self.use_cgrag and self.print_cgrag:
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.BLUE}\nCGRAG Guidance: \n\n{Style.RESET_ALL}"
            )
        else:
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.GREEN}\nAssistant: \n\n{Style.RESET_ALL}"
            )
        if self.use_cgrag:
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.WHITE}\r(generating contextual guidance...){Style.RESET_ALL}"
            )
        else:
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.WHITE}\r(thinking...){Style.RESET_ALL}"
            )
        sys.stdout.flush()

    def print_cgrag_output(self, cgrag_output):
        if self.print_cgrag:
            sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
            sys.stdout.write(
                Style.BRIGHT + Fore.WHITE + f"\r\nContextual Guide Output:\r{cgrag_output}\n\n" + Style.RESET_ALL
            )
            sys.stdout.write(
                Style.BRIGHT + Fore.GREEN + "Assistant: \n\n" + Style.RESET_ALL
            )
        else:
            sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
        sys.stdout.write("\r(thinking...)" + Style.RESET_ALL)
        sys.stdout.flush()

    def create_cgrag_prompt(self, base_prompt):
        return f"""What information related to the included files is important to answering the following 
user prompt?

User prompt: '{base_prompt}'

First, study the solution structure in Readme.md. Respond with only a list of information and concepts. 
Include in the list all information and concepts necessary to answer the prompt, including those in the included files 
and those which the included files do not contain. Your response will be used to create an LLM embedding that will be 
used in a RAG to find the appropriate files which are needed to answer the user prompt. There may be many files not 
currently included which have more relevant information, so your response must include the most important concepts and 
information required to accurately answer the user prompt. Keep the list length to around 20 items. If the prompt is 
referencing code, list specific class, function, and variable names as applicable to answering the user prompt. 
Interface and the actual implementation class must be synchronized. At the end of the reply, suggest a list of files that 
you think are affected and may need to be updated or created, including the file path besides the filename.
"""

    def run_stream_processes(self, user_input, write_to_stdout):
        if self.use_cgrag:
            relevant_full_text = self.build_relevant_full_text(user_input)
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.GREEN}\n!!! Initial Search result Length: {len(relevant_full_text)}, First 1000 characters:\n\n{Style.RESET_ALL}"
            )
            sys.stdout.write(f"{relevant_full_text[:1000]} ...\n\n{Style.RESET_ALL}")
            sys.stdout.flush()
            cgrag_prompt = self.create_cgrag_prompt(user_input)
            sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
            sys.stdout.write(
                Style.BRIGHT + Fore.GREEN + f"\r!!! concate initial search result with below as Prompt to get Contextual Guide: '{cgrag_prompt}'\n\n" + Style.RESET_ALL
            )
            sys.stdout.flush()
            cgrag_content = relevant_full_text + cgrag_prompt
            cgrag_history = copy.deepcopy(self.chat_history)
            cgrag_prompt_history = self.create_user_history(
                cgrag_content, cgrag_content
            )
            cgrag_history.append(cgrag_prompt_history)
            self.cull_history_list(cgrag_history)
            cgrag_generator = self.call_completion(cgrag_history)
            guidance_history = self.create_empty_history()
            guidance_history = self.run_completion_generator(
                cgrag_generator, guidance_history, False
            )
            relevant_full_text = self.build_relevant_full_text(
                guidance_history["content"]
            )
            # add before full text # self.add_user_history(guidance_history["content"], guidance_history["content"])
            relevant_full_text = "\nContext Guidance:\n" + guidance_history["content"] + "\nFile Snippets:\n" + relevant_full_text

            self.print_cgrag_output(guidance_history["content"])
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.GREEN}\n!!! Contextual Guide Search result Length: {len(relevant_full_text)}, First 1000 characters:\n\n{Style.RESET_ALL}"
            )
            sys.stdout.write(f"{relevant_full_text[:8000]} ...\n\n{Style.RESET_ALL}")
            sys.stdout.flush()
        else:
            relevant_full_text = self.build_relevant_full_text(user_input)

        prompt = self.create_prompt(user_input, "") # create prompt to generate a list of files to output
        sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
        sys.stdout.write(
            Style.BRIGHT + Fore.GREEN + f"\r!!! concate Contextual Guide search result with below as prompt to list all files output:'{prompt}'\n\n" + Style.RESET_ALL
        )
        sys.stdout.flush()
        # last parameter specifies if R1 is used
        first_round = self.run_basic_chat_stream(prompt, relevant_full_text, False, False)
        try:
            file_list = json.loads(first_round)
            for outfile in file_list:
                sys.stdout.write(
                    Style.BRIGHT + Fore.WHITE + f"\r{outfile}\n" + Style.RESET_ALL
                )
            sys.stdout.flush()
            sys.stdout.write(
                f"{Style.BRIGHT}{Fore.BLUE}Generate these files? (Y/N): {Style.RESET_ALL}"
            )
            apply_changes = ask_prompt("", multiline=False).strip().lower()
            if write_to_stdout:
                sys.stdout.write("\n")
            if apply_changes == "y" and isinstance(file_list, list):
                for outfile in file_list:
                    prompt = self.create_prompt(user_input, outfile) # create prompt for each file to be output
                    sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
                    sys.stdout.write(
                        Style.BRIGHT + Fore.GREEN + f"\r!!! concate Contextual Guide search result with below as prompt to generate file:'{prompt}'\n\nGenerating {outfile}...\n\n" + Style.RESET_ALL
                    )
                    sys.stdout.flush()
                    # self.call_completion_fc(prompt, relevant_full_text, outfile)
                    stream_output = self.run_basic_chat_stream(prompt, relevant_full_text, False)
                    self.run_post_stream_processes(user_input, stream_output, False)
                return f"""files {file_list} were successfully written to folder"""
            else:
                return "Task completed!"
        except json.JSONDecodeError:
            return first_round

