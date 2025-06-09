import os
import asyncio

from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.agents.strategies.selection.kernel_function_selection_strategy import (
    KernelFunctionSelectionStrategy,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel



# class ApprovalTerminationStrategy(TerminationStrategy):
#     """A strategy for determining when an agent should terminate."""
 
#     async def should_agent_terminate(self, agent, history):
#         """Check if the agent should terminate."""
#         return NotImplementedError("Code to be implemented by the student")


# async def run_multi_agent(input: str):
#     """implement the multi-agent system."""
#     return responses


import os
import asyncio
import re
import subprocess
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from dotenv import load_dotenv
from semantic_kernel.functions import KernelFunctionFromPrompt, kernel_function
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)

import nest_asyncio
nest_asyncio.apply()
load_dotenv()

# Define agent names
BA = "BusinessAnalyst"
SE = "SoftwareEngineer"
PO = "ProductOwner"

class FileSavePlugin:
    """A Plugin used for saving HTML content to a file."""

    @kernel_function(description="Extracts HTML content and saves it to a file", name="extract_and_save_html")
    async def extract_and_save_html(self, content: str):
        # Define a regular expression pattern to match HTML content
        html_pattern = re.compile(r'<html.*?>.*?</html>', re.DOTALL | re.IGNORECASE)

        # Extract HTML content using the pattern
        match = html_pattern.search(content)
        if match:
            html_content = match.group(0)
            file_path = "index.html"
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(html_content)
            # Push to GitHub
            # Define the path to the script relative to the current script location
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, '../../push_to_github.sh')
            print(f"Resolved script path: {script_path}")
            
            commit_message = "Automated commit: Changes approved"
            # Call the Bash script with subprocess
            commit_message = "Automated commit: Changes approved"
            subprocess.run(['bash', '../../push_to_github.sh', commit_message], check=True)
            
            return f"HTML content saved to {file_path}"
        else:
            return "No HTML content found in the provided text."

def initialize_kernel():
    kernel = Kernel()
    # #Challene 02 - Add Kernel
    chat_completion_service = AzureChatCompletion(
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
   
    kernel.add_service(chat_completion_service)
    return kernel

# Define a custom termination strategy
class ApprovalTerminationStrategy(TerminationStrategy):
    """A strategy for determining when an agent should terminate."""
    
    async def should_agent_terminate(self, agent, history):
        """Check if the agent should terminate."""
        for message in history:
            if "APPROVED" in message.content:
                return True
        return False

# Define agent personas
business_analyst_persona = """
    You are a Business Analyst which will take the requirements from the user (also known as a 'customer') 
    and create a project plan for creating the requested app. The Business Analyst understands the user 
    requirements and creates detailed documents with requirements and costing. The documents should be 
    usable by the SoftwareEngineer as a reference for implementing the required features, and by the 
    Product Owner for reference to determine if the application delivered by the Software Engineer meets 
    all of the user's requirements.
    """

software_engineer_persona = """
    You are a Software Engineer, and your goal is create a web app using HTML and JavaScript by taking 
    into consideration all the requirements given by the Business Analyst. The application should 
    implement all the requested features. Deliver the code to the Product Owner for review when completed. You can also ask questions of the BusinessAnalyst to clarify any requirements that are unclear.
    """

product_owner_persona = """
    You are the Product Owner which will review the software engineer's code to ensure all user requirements 
    are completed. You are the guardian of quality, ensuring the final product meets all specifications. 
    IMPORTANT: Verify that the Software Engineer has shared the HTML code using the format ```html [code] ```. 
    This format is required for the code to be saved and pushed to GitHub. Once all client requirements 
    are completed and the code is properly formatted, reply with 'READY FOR USER APPROVAL'. If there are 
    missing features or formatting issues, you will need to send a request back to the SoftwareEngineer 
    or BusinessAnalyst with details of the defect.
    """

async def run_multi_agent(user_input: str):
    """Implement the multi-agent system."""
    # Initialize the Kernel
    kernel = initialize_kernel()

    # Get the AI Service settings
    settings = kernel.get_prompt_execution_settings_from_service_id("default")

    # Configure the function choice behavior to auto invoke kernel functions
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # Add the Plugin to the Kernel
    kernel.add_plugin(FileSavePlugin(), plugin_name="FileSavePlugin")
   
    # Create agents
    business_analyst_agent = ChatCompletionAgent(
        name=BA,
        instructions=business_analyst_persona,
        kernel=kernel
    )
    print("Business Analyst Agent Initialized")

    software_engineer_agent = ChatCompletionAgent(
        name=SE,
        instructions=software_engineer_persona,
        kernel=kernel
    )
    print("Software Engineer Agent Initialized")

    product_owner_agent = ChatCompletionAgent(
        name=PO,
        instructions=product_owner_persona,
        kernel=kernel
    )
    print("Product Owner Agent Initialized")

    # Define a selection function to determine which agent should take the next turn.
    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""Examine the provided RESPONSE and choose the next participant.
        State only the name of the chosen participant without explanation.
        Never choose the participant named in the RESPONSE.

        Choose only from these participants:
        - {BA}
        - {SE}
        - {PO}

        Rules:
        - If RESPONSE is user input, it is {BA}'s turn.
        - If RESPONSE is by {BA}, it is {SE}'s turn.
        - If RESPONSE is by {SE}, it is {PO}'s turn.
        - If RESPONSE is by {PO}, the process is complete.

        RESPONSE:
        {{{{$lastmessage}}}}
        """,
            )
    
    # Define a termination function where the process ends after the saver agent confirms.
    termination_keyword = "APPROVED"

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
            Examine the RESPONSE and determine whether the content has been APPROVED.
            If the content has been saved, respond with a single word without explanation: {termination_keyword}.

            RESPONSE:
            {{{{$lastmessage}}}}
        """,)

    history_reducer = ChatHistoryTruncationReducer(target_count=3)

    # Create an AgentGroupChat with the agents
    group_chat = AgentGroupChat(
        agents=[business_analyst_agent, software_engineer_agent, product_owner_agent],
        selection_strategy=KernelFunctionSelectionStrategy(
            initial_agent=business_analyst_agent,
            function=selection_function,
            kernel=kernel,
            result_parser=lambda result: str(result.value[0]).strip() if result.value[0] is not None else SE,
            history_variable_name="lastmessage",
            history_reducer=history_reducer,
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[product_owner_agent],
            function=termination_function,
            kernel=kernel,
            result_parser=lambda result: termination_keyword in str(result.value[0]).lower(),
            history_variable_name="lastmessage",
            maximum_iterations=5,
            history_reducer=history_reducer,
        ),
    )

    is_complete = False
    conversation_history = []

    # Create a ChatMessageContent object
    message_content = ChatMessageContent(role=AuthorRole.USER, content=user_input)

    # Add the current user_input to the chat
    await group_chat.add_chat_message(message_content)

    conversation_history.append({"role": "user", "content": user_input})

    try:
        async for response in group_chat.invoke():
            if response is None or not response.name:
                continue
            print(f"# {response.role} - {response.name or '*'}: '{response.content}'")
            conversation_history.append({
                "role": response.role,
                "content": response.content
            })

            # Check for approval keyword
            if "READY FOR USER APPROVAL" in response.content.upper():
                is_complete = True
                break

    except Exception as e:
        conversation_history.append({"role": "error", "content": "Please Try again"})

    return {"messages": conversation_history}