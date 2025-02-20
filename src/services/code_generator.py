import json
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from typing import Generator
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from openai import AzureOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.base import BaseChatModel
from langchain.schema.messages import BaseMessage
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List, Optional, Union
from services.config_manager import ConfigManager
import logging
from utils.logger_config import setup_logger

# Get logger for this module
logger = logging.getLogger(__name__)

class CodeGenerator:
    def __init__(self):
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Get model configuration from config manager
        self.model_provider = self.config_manager.get_config('MODEL_PROVIDER', 'openai').lower()
        self.model_name = self.config_manager.get_config('MODEL_NAME', 'gpt-4')
        
        # Debug logging
        logger.debug("CodeGenerator initialized with:")
        logger.debug(f"Model Provider: {self.model_provider}")
        logger.debug(f"Model Name: {self.model_name}")

    def extract_interacted_elements(self, cleaned_history_path: str) -> None:
        """
        Extract interacted elements from cleaned history and save to a new JSON file
        
        Args:
            cleaned_history_path: Path to the cleaned history JSON file
        """
        try:
            logger.info("Starting extraction of interacted elements")
            
            # Read the cleaned history
            with open(cleaned_history_path, 'r') as f:
                history_data = json.load(f)
            logger.debug(f"Successfully loaded history data from {cleaned_history_path}")
            
            # Extract timestamp from the filename
            cleaned_history_path_str = str(cleaned_history_path)
            timestamp = cleaned_history_path_str.split('cleaned_history_')[-1].split('.json')[0]
            logger.debug(f"Extracted timestamp: {timestamp}")
            
            # Initialize list to store interacted elements
            interacted_elements = []
            
            # Iterate through history and extract interacted elements
            history_entries = history_data.get('history', [])
            logger.debug(f"Found {len(history_entries)} history entries")
            
            for entry in history_entries:
                state = entry.get('state', {})
                elements = state.get('interacted_element', [])
                logger.debug(f"Found {len(elements)} elements in history entry")
                
                for element in elements:
                    if element and isinstance(element, dict):  # Skip None values and ensure it's a dictionary
                        # Extract required attributes
                        element_data = {
                            'tag_name': element.get('tag_name'),
                            'xpath': element.get('xpath'),
                            'attributes': element.get('attributes'),
                            'css_selector': element.get('css_selector'),
                            'entire_parent_branch_path': element.get('entire_parent_branch_path')
                        }
                        interacted_elements.append(element_data)
                        logger.debug(f"Added element with tag {element_data['tag_name']}")
            
            # Create output file path in the same timestamp folder as cleaned history
            history_folder = Path(cleaned_history_path).parent
            elements_file_path = history_folder / f'elements_{timestamp}.json'
            
            # Save extracted elements to new JSON file
            with open(elements_file_path, 'w') as f:
                json.dump({'interacted_elements': interacted_elements}, f, indent=2)
            
            # Verify the file was saved correctly
            if elements_file_path.exists():
                logger.debug(f"Successfully saved {len(interacted_elements)} interacted elements to {elements_file_path}")
            else:
                logger.error(f"Failed to save elements file at {elements_file_path}")
                raise FileNotFoundError(f"Elements file was not created at {elements_file_path}")
            
        except Exception as e:
            logger.error(f"Error extracting interacted elements: {str(e)}")
            raise

    def get_llm(self):
        """
        Configure and return the appropriate LLM based on environment settings
        """
        if self.model_provider == 'anthropic':
            logger.info("Using Anthropic configuration")
            return ChatAnthropic(
                model=self.model_name,
                anthropic_api_key=self.config_manager.get_config('ANTHROPIC_API_KEY'),
                temperature=0.7,
                streaming=True
            )
        elif self.model_provider == 'azure':
            logger.info("Using Azure OpenAI configuration")
            azure_endpoint = self.config_manager.get_config('AZURE_OPENAI_ENDPOINT')
            deployment_name = self.config_manager.get_config('AZURE_DEPLOYMENT_NAME')
            api_version = self.config_manager.get_config('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')
            api_key = self.config_manager.get_config('AZURE_OPENAI_API_KEY')
            
            logger.info(f"Azure OpenAI Endpoint: {azure_endpoint}")
            logger.info(f"Azure Deployment Name: {deployment_name}")
            
            return AzureChatOpenAI(
                api_version=api_version,
                azure_deployment=deployment_name,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                temperature=0.7,
                max_tokens=None,
                timeout=None,
                model_name=deployment_name,
                streaming=True
            )
        elif self.model_provider == 'deepseek':
            logger.info("Using DeepSeek configuration")
            return ChatOpenAI(
                model=self.model_name,
                api_key=self.config_manager.get_config('DEEPSEEK_API_KEY'),
                openai_api_base="https://api.deepseek.com/v1",
                temperature=0.7,
                streaming=True
            )
        elif self.model_provider == 'groq':
            logger.info("Using Groq configuration")
            return ChatGroq(
                model=self.model_name,
                api_key=self.config_manager.get_config('GROQ_API_KEY'),
                temperature=0.7,
                streaming=True
            )
        elif self.model_provider == 'google':
            google_api_key = self.config_manager.get_config('GOOGLE_API_KEY')
            logger.info("Using Google configuration")
            logger.debug(f"Google API key length: {len(google_api_key) if google_api_key else 0}")
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                api_key=google_api_key,
                temperature=0.7,
                streaming=True
            )
        else:
            logger.info("Using OpenAI configuration")
            return ChatOpenAI(
                model=self.model_name,
                api_key=self.config_manager.get_config('OPENAI_API_KEY'),
                temperature=0.7,
                streaming=True
            )

    def generate_typescript_code(self, cleaned_history_path: str, prompt_template_path: str) -> str:
        """
        Generate TypeScript code using the configured LLM based on cleaned history and prompt template
        
        Args:
            cleaned_history_path: Path to the cleaned history JSON file
            prompt_template_path: Path to the prompt template file
            
        Returns:
            str: Generated TypeScript code
        """
        # First extract and save interacted elements
        self.extract_interacted_elements(cleaned_history_path)
        
        # Read the cleaned history
        with open(cleaned_history_path, 'r') as f:
            history_content = f.read()
            
        # Read the prompt template
        with open(prompt_template_path, 'r') as f:
            prompt_template = f.read()
            
        # Replace placeholder in prompt with history content
        final_prompt = prompt_template.replace('{json_file_content}', history_content)
        
        # Log the final prompt
        logger.debug(f"\n=== Final Prompt Sent to {self.model_provider.upper()} LLM ===")
        logger.debug(final_prompt)
        logger.debug("=== End of Prompt ===\n")
        
        # Get LLM instance
        llm = self.get_llm()
        
        # Create messages
        messages = [
            SystemMessage(content="You are a Playwright TypeScript code generator. Generate only the code with no additional text."),
            HumanMessage(content=final_prompt)
        ]
        
        # Get response
        response = llm.invoke(messages)
        return response.content

    def generate_typescript_code_stream(self, cleaned_history_path: str, prompt_template_path: str) -> Generator[str, None, None]:
        """
        Generate TypeScript code using configured LLM with streaming
        
        Args:
            cleaned_history_path: Path to the cleaned history JSON file
            prompt_template_path: Path to the prompt template file
            
        Yields:
            str: Chunks of generated TypeScript code
        """
        try:
            logger.info(f"\n=== Starting Code Generation Process using {self.model_provider.upper()} ===")
            
            # First extract and save interacted elements
            self.extract_interacted_elements(cleaned_history_path)
            
            # Read the cleaned history
            logger.debug(f"Reading history from: {cleaned_history_path}")
            with open(cleaned_history_path, 'r') as f:
                history_content = f.read()
            logger.debug(f"History content length: {len(history_content)} characters")
                
            # Read the prompt template
            logger.debug(f"Reading prompt template from: {prompt_template_path}")
            with open(prompt_template_path, 'r') as f:
                prompt_template = f.read()
            logger.debug(f"Prompt template length: {len(prompt_template)} characters")
                
            # Replace placeholder in prompt with history content
            final_prompt = prompt_template.replace('{json_file_content}', history_content)
            logger.debug(f"Final prompt length: {len(final_prompt)} characters")
            
            # Log the final prompt
            logger.debug(f"\n=== Final Prompt Sent to {self.model_provider.upper()} LLM ===")
            logger.debug(final_prompt)
            logger.debug("=== End of Prompt ===\n")
            
            # Get LLM instance
            llm = self.get_llm()
            
            # Create messages
            messages = [
                SystemMessage(content="You are a Playwright TypeScript code generator. Generate only the code with no additional text."),
                HumanMessage(content=final_prompt)
            ]
            
            logger.info(f"Calling {self.model_provider.upper()} API with streaming enabled...")
            
            # Stream the response
            total_content = ""
            chunk_count = 0
            
            for chunk in llm.stream(messages):
                chunk_content = chunk.content
                total_content += chunk_content
                chunk_count += 1
                yield chunk_content
            
            logger.info(f"\n=== Code Generation Complete ===")
            logger.debug(f"Total chunks received: {chunk_count}")
            logger.debug(f"Total content length: {len(total_content)}")
            
            logger.debug("\n=== Generated TypeScript Code ===")
            logger.debug(total_content)
            logger.debug("\n=== End of Generated Code ===\n")
            
        except Exception as e:
            logger.error(f"\n=== Error in Code Generation ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            raise 