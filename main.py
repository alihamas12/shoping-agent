import os
from dotenv import load_dotenv
from agent import agent_executor
from langchain_core.messages import HumanMessage, AIMessage
from session_manager import session_manager
import time

def run_agent():
    load_dotenv()
    A
    conversation_history = []
    thread_id = "default_thread"
    session_id = "default_session"
    
    print("AI Automation Agent Ready! Type 'exit' to quit")
    print("I can securely store your personal info and purchase items from any e-commerce site!")
    print("Example: 'Store my name as John Doe, email as john@example.com, phone as 123-456-7890'")
    print("Example: 'Store my address as 123 Main St, City, State, ZIP'")
    print("Example: 'Store my credit card as 1234-5678-9012-3456'")
    print("Example: 'Store my password as mypassword123'")
    print("Example: 'Buy a laptop on Amazon'")
    print("Example: 'Buy a TV on BestBuy'")
    print("Example: 'Buy a phone on Walmart'")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:

            session_manager.close_session(session_id)
            break
            

        conversation_history.append(HumanMessage(content=user_input))
        

        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            response = agent_executor.stream(
                {"messages": conversation_history, "session_id": session_id},
                config
            )
            

            full_response = ""
            for chunk in response:
                if "agent" in chunk:
                    content = chunk['agent']['messages'][0].content
                    full_response += content
                    print(f"Agent: {content}")
                elif "tools" in chunk:
                    print(f"Using tools: {list(chunk['tools'].keys())}")
            
            conversation_history.append(AIMessage(content=full_response))
            
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]
                
        except Exception as e:
            print(f"Error: {str(e)}")

            conversation_history.append(AIMessage(content=f"Error: {str(e)}"))
            continue

if __name__ == "__main__":
    run_agent()