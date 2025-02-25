import streamlit as st
import anthropic
from datetime import datetime
import json
import re
import pyperclip
from typing import List, Dict, Optional

class ClaudeChatbot:
    def __init__(self):
        self.system_prompt = """You are an IT administration expert specializing in PowerShell scripting, batch scripting, 
        SCCM (Microsoft Configuration Manager), Group Policy Objects (GPO), Active Directory, and various endpoint management tools. 
        When providing scripts or code, you should format them as distinct artifacts, similar to how Claude does in its web interface. 
        Each code artifact should be properly formatted in markdown with syntax highlighting and should be treated as a separate, 
        copyable element. Focus on providing practical, secure, and efficient solutions for enterprise IT environments."""
        
        self.default_params = {
            "model": "claude-3-7-sonnet-20250219",
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 0.7,
            "extended_thinking": False
        }

    def initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'api_key' not in st.session_state:
            st.session_state.api_key = ''
        if 'parameters' not in st.session_state:
            st.session_state.parameters = self.default_params.copy()

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown text"""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        code_blocks = []
        
        for match in matches:
            language = match.group(1) or ''
            code = match.group(2).strip()
            code_blocks.append({
                'language': language,
                'code': code
            })
        
        return code_blocks

    def format_message(self, message: str, is_user: bool) -> str:
        """Format chat messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sender = "You" if is_user else "Claude"
        return f"**{sender}** ({timestamp}):\n\n{message}\n\n"

    def save_chat_history(self):
        """Save chat history to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(st.session_state.messages, f, indent=2)
        
        return filename

    def create_chat_interface(self):
        """Create the main chat interface"""
        st.title("Claude IT Administration Assistant")
        
        # Sidebar for configuration
        with st.sidebar:
            st.header("Configuration")
            
            # API Key input
            api_key = st.text_input("Enter Anthropic API Key:", 
                                  type="password", 
                                  value=st.session_state.api_key)
            
            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key

            # Model parameters
            st.subheader("Model Parameters")
            temperature = st.slider("Temperature", 
                                 min_value=0.0, 
                                 max_value=1.0, 
                                 value=st.session_state.parameters['temperature'],
                                 step=0.1)
            
            max_tokens = st.number_input("Max Tokens",
                                      min_value=1,
                                      max_value=4096,
                                      value=st.session_state.parameters['max_tokens'])
            
            top_p = st.slider("Top P",
                           min_value=0.0,
                           max_value=1.0,
                           value=st.session_state.parameters['top_p'],
                           step=0.1)
            
            extended_thinking = st.toggle("Enable Extended Thinking Mode", 
                                     value=st.session_state.parameters.get('extended_thinking', False),
                                     help="Enables Claude's extended thinking/reasoning mode for more complex questions")

            # Update parameters if changed
            st.session_state.parameters.update({
                'temperature': temperature,
                'max_tokens': max_tokens,
                'top_p': top_p,
                'extended_thinking': extended_thinking
            })

            # Save chat button
            if st.button("Save Chat History"):
                filename = self.save_chat_history()
                st.success(f"Chat saved to {filename}")

            # Clear chat button
            if st.button("Clear Chat"):
                st.session_state.messages = []
                st.rerun()

        # Main chat area
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Extract and display code blocks
                code_blocks = self.extract_code_blocks(message["content"])
                for idx, block in enumerate(code_blocks):
                    with st.expander(f"Code Artifact {idx + 1}"):
                        st.code(block['code'], language=block['language'])
                        if st.button(f"Copy Code {idx + 1}"):
                            pyperclip.copy(block['code'])
                            st.success("Code copied to clipboard!")

        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            if not st.session_state.api_key:
                st.error("Please enter your API key in the sidebar.")
                return

            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get Claude's response
            try:
                client = anthropic.Client(api_key=st.session_state.api_key)
                
                # Prepare the messages list (only user and assistant messages)
                messages = [
                    {
                        "role": msg["role"],
                        "content": msg["content"]
                    } for msg in st.session_state.messages
                ]

                # Get response from Claude with system prompt as separate parameter
                # Include extended thinking parameter if enabled
                message_params = {
                    "model": st.session_state.parameters["model"],
                    "temperature": st.session_state.parameters["temperature"],
                    "max_tokens": st.session_state.parameters["max_tokens"],
                    "system": self.system_prompt,
                    "messages": messages
                }
                
                # Add extended thinking parameter if enabled
                if st.session_state.parameters.get("extended_thinking", False):
                    message_params["extended_thinking"] = True
                
                response = client.messages.create(**message_params)

                # Add Claude's response to chat
                assistant_message = response.content[0].text
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_message}
                )
                
                with st.chat_message("assistant"):
                    st.markdown(assistant_message)
                    
                    # Extract and display code blocks
                    code_blocks = self.extract_code_blocks(assistant_message)
                    for idx, block in enumerate(code_blocks):
                        with st.expander(f"Code Artifact {idx + 1}"):
                            st.code(block['code'], language=block['language'])
                            if st.button(f"Copy Code {idx + 1}"):
                                pyperclip.copy(block['code'])
                                st.success("Code copied to clipboard!")

            except Exception as e:
                st.error(f"Error: {str(e)}")

def main():
    chatbot = ClaudeChatbot()
    chatbot.initialize_session_state()
    chatbot.create_chat_interface()

if __name__ == "__main__":
    main()