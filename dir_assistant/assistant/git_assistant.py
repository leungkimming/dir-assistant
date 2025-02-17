import os
import sys

from colorama import Fore, Style
from prompt_toolkit import prompt

from dir_assistant.assistant.cgrag_assistant import CGRAGAssistant


class GitAssistant(CGRAGAssistant):
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
        )
        self.commit_to_git = commit_to_git

    def create_prompt(self, user_input, outfile):
        if not self.commit_to_git:
            return user_input
        
        # Create a promput to output the required file -- outfile
        if outfile != "":
#             return f"""User Prompt:
# {user_input}
# ----------------------------------
# Given the user prompt above and included file snippets, respond with contents of the '{outfile}' file. Just 
# ONE '{outfile}' file and no other files. Call the 'output_file' function with the file's pathname and contents 
# as parameters to output the file. To modify an existing file, always respond with the entire contents 
# of the new version of the file. Ensure white space and new lines are consistent with the original.

# Example response:
# call output_file('{outfile}', '''
# import React from 'react';

# if __name__ == "__main__":
#     print("Hello, World!")
# ''');
# """
                return f"""User Prompt:
{user_input}
----------------------------------
Given the user prompt above and included file snippets, respond with the contents of the '{outfile}' file that has the 
changes the user prompt requested. Just ONE '{outfile}' file and no other files. Do not provide an introduction, summary, 
or conclusion. Only respond with the file's contents. Do not respond with surrounding markdown. Namespace should only 
contain the project's name and never add subfolders to a Namespace. Add the filename of the file as the first line of 
that file's response. Keep existing file's content by adding new coding. Always respond with the entire contents of the 
new version of the file. Ensure white space and new lines are consistent with the original.

Example response:
{outfile}
import React from 'react';

if __name__ == "__main__":
    print("Hello, World!")
''');

Real response:
"""
        else:
            # First, ask the LLM if output file is required
            should_diff_output = self.run_one_off_completion(
                f"""Does the prompt below request changes to files? 
Respond only with one word: "YES" or "NO". Do not respond with additional words or characters, only "YES" or "NO".
User prompt:
{user_input}
"""
            )
            sys.stdout.write(Style.BRIGHT + Fore.WHITE + "\r" + (" " * 36))
            sys.stdout.write(
                Style.BRIGHT + Fore.GREEN + f"\r!!! Ask LLM if your prompt need to change files? Answer='{should_diff_output}'\n\n" + Style.RESET_ALL
            )
            if "YES" in should_diff_output:
                self.should_diff = True
            elif "NO" in should_diff_output:
                self.should_diff = False
            else:
                self.should_diff = None

            # File output is required, create a Prompt to ask LLM for a list of file paths to output
            if self.should_diff:
                return f"""User Prompt:
{user_input}
----------------------------------
Given the user prompt above and included Context Guidance and file snippets, list out the pathname 
of all files that were being mentioned in the Context Guidance and may need to be updated or created. 
Interface and acutual Implementation must be synchronized. Do not respond with additional words or 
characters or surrounding markdown. Just respond with the list of files in plain text as in the example below.

Example response:
["src/hello_world.tsx", "src/hello_world.css", "src/main.tsx"]

Real response:
"""
            # File output is NOT required. return the original user prompt
            else:
                return user_input

    def run_post_stream_processes(self, user_input, stream_output, write_to_stdout):
        if (
            not self.commit_to_git or not self.should_diff
        ) and not self.git_apply_error:
            return super().run_post_stream_processes(
                user_input, stream_output, write_to_stdout
            )
        else:
            if stream_output == "":
                return True
            # sys.stdout.write(
            #     f"{Style.BRIGHT}{Fore.BLUE}Apply these changes? (Y/N): {Style.RESET_ALL}"
            # )
            # apply_changes = prompt("", multiline=False).strip().lower()
            # if write_to_stdout:
            #     sys.stdout.write("\n")
            apply_changes = "y"
            if apply_changes == "y":
                output_lines = stream_output.split("\n")
                changed_filepath = output_lines[0].strip()
                file_slice = output_lines[1:]
                if file_slice[0].startswith("```"):
                    file_slice = file_slice[1:]
                if file_slice[-1].endswith("```"):
                    file_slice = file_slice[:-1]
                cleaned_output = "\n".join(file_slice)
                try:
                    os.makedirs(os.path.dirname(changed_filepath), exist_ok=True)
                    with open(changed_filepath, "w", encoding="utf-8") as changed_file:
                        changed_file.write(cleaned_output)
                except Exception as e:
                    sys.stdout.write(
                        f"\n{Style.BRIGHT}{Fore.RED}Terminated with Error: {e}{Style.RESET_ALL}\n\n"
                    )
                    sys.stdout.flush()
                    return True
                # os.system("git add .")
                # os.system(f'git commit -m "{user_input.strip()}"')
                if write_to_stdout:
                    sys.stdout.write(
                        f"\n{Style.BRIGHT}Changes written to files.{Style.RESET_ALL}\n\n"
                    )
                    sys.stdout.flush()
            return False

    def stream_chat(self, user_input):
        self.git_apply_error = None
        super().stream_chat(user_input)
