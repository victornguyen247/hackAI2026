import os
import json
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')
model_v3 = genai.GenerativeModel('gemini-3.1-pro-preview')
#model_v3 = genai.GenerativeModel('gemini-2.5-flash')

class Service:
    @staticmethod
    def summarize_goal(goal: str) -> str:
        """
        Summarizes a long user goal into keywords/role title.
        """
        prompt = f"Summarize this learning goal into a short, title (e.g., 'Fullstack Developer', 'Python Programming'): \"{goal}\". Return ONLY the title text. if {goal} is not a actual goal, return empty string"
        try:
            response = model.generate_content(prompt)
            title = response.text.strip().replace('"', '')
            return title if len(title) > 0 else ""
        except:
            return ""

    @staticmethod
    def generate_subtree(topic: str, main_goal: str, current_level: int, max_depth: int = 1) -> List[Dict]:
        """
        Generates a subtree for a specific topic with a limited depth.
        """
        prompt = f"""
        User Goal: "{main_goal}"
        Current Topic to Expand: "{topic}" (at level {current_level})
        
        Act as an expert instructor. Continue building the learning path by expanding "{topic}" into more detailed sub-topics.
        Generate exactly {max_depth} more levels of depth for this branch.
        
        RULES:
        1. Hierarchical structure: level {current_level + 1} for immediate children.
        2. Descriptions: Concise but informative.
        3. Format: Return ONLY a JSON array of objects.
        
        FIELDS:
        - "title": (string)
        - "description": (string)
        - "parent_title": (string) MUST BE "{topic}" for immediate children.
        - "level": (int) {current_level + 1}.
        - "is_leaf": (boolean) Set to true if this node is a specific, final skill or tool. Set to false if it's a category that could be expanded further (even if you don't expand it now).
        
        Limit to 4-6 closest related nodes per prompt to stay focused.
        """
        
        try:
            print(f"DEBUG: Generating subtree for: {topic} (Prompts used/remaining...)")
            response = model.generate_content(prompt)
            content = response.text
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx == -1 or end_idx == 0:
                print(f"DEBUG WARNING: No JSON array found in response for {topic}")
                return []
                
            json_str = content[start_idx:end_idx]
            return json.loads(json_str)
        except Exception as e:
            print(f"DEBUG ERROR: Subtree generation error for {topic}: {e}")
            return []

    @staticmethod
    def expand_topic(topic: str, goal_context: str) -> List[Dict]:
        """
        Phase 2/3: Expands a concept into its immediate sub-concepts.
        If the topic is very specific (a 'leaf' skill) and has no meaningful sub-concepts, return [].
        """
        prompt = f"""
        Objective: Expand "{topic}" within the learning journey for "{goal_context}".
        
        Task: Identify immediate related sub-concepts or building blocks for "{topic}". 
        IMPORTANT: Use commonly shared concepts if they exist (e.g., both 'React' and 'Vue' might share 'State Management').
        If "{topic}" is already a very specific tool or a single piece of information that is trivial to expand further, return an empty JSON array [].
        
        Return ONLY a JSON array of objects.
        Fields:
        - "title": (string) Short name of the sub-concept.
        - "description": (string) Brief overview.
        - "is_expandable": (boolean) true if this sub-concept can be broken down further, false if it's a specific final skill.
        """
        try:
            response = model.generate_content(prompt)
            content = response.text
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx == -1: return []
            return json.loads(content[start_idx:end_idx])
        except:
            return []

    @staticmethod
    def generate_learning_route(goal: str) -> List[Dict]:
        """
        Phase 1: Generate the Root and immediate high-level concept objects.
        """
        prompt = f"""
        Act as an expert instructor. The user wants to learn: "{goal}".
        
        Phase 1: 
        1. Define the ROOT node (the goal itself).
        2. Identify the core "Majors" or "Concepts" (Level 2) that form the foundation for "{goal}".
        
        Return ONLY a JSON array of objects.
        Fields:
        - "title": (string)
        - "description": (string)
        - "parent_title": (string or null) - use null for the root.
        - "level": (integer) 1 for root, 2 for concepts.
        - "is_expandable": (boolean) always true for these concepts.
        """
        try:
            response = model.generate_content(prompt)
            content = response.text
            if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            return json.loads(content[start_idx:end_idx])
        except:
            return []

    @staticmethod
    def get_resources_for_topic(topic: str, goal_context: str) -> List[Dict]:
        prompt = f"""
        Act as a professional educational curator. Provide 3-5 high-quality, CURRENT, and ACCESSIBLE learning resources for the topic "{topic}" within the context of learning "{goal_context}".
        
        CRITICAL LINK RULES:
        1. VALIDITY: Only provide URLs that actually exist. Prioritize major platforms like YouTube, Official Documentation, Coursera, or reputable blogs (Medium, Dev.to).
        2. ACCESS: Ensure the resources are free to access if possible, or very high-quality if paid.
        3. VARIETY: Include a mix of videos(2 resources as possible) , articles, and documentation.
        
        Return ONLY a JSON array of objects.
        Fields:
        - "type": (string) "video", "article", or "documentation"
        - "title": (string)
        - "url": (string)
        - "description": (string) Concise summary of the content.
        
        Example Output Format:
        [
          {{"type": "video", "title": "React Basics", "url": "https://youtube.com/...", "description": "..."}}
        ]
        """
        try:
            print(f"DEBUG: Fetching resources for topic: {topic}")
            response = model_v3.generate_content(prompt)
            content = response.text.strip()
            
            # More robust JSON cleaning
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx == -1 or end_idx == 0:
                print(f"DEBUG ERROR: No JSON array found in resource response for {topic}. Content: {content[:200]}...")
                return []
                
            json_str = content[start_idx:end_idx]
            resources = json.loads(json_str)
            print(f"DEBUG: Successfully found {len(resources)} resources for {topic}")
            return resources
        except Exception as e:
            print(f"DEBUG ERROR: Resource generation failed for {topic}: {e}")
            return []

    @staticmethod
    def chat(messages: List[Dict], goal_context: str) -> str:
        """
        Chat with the user about their learning journey.
        messages: list of {"role": "user/assistant", "content": "..."}
        """
        system_prompt = f"""
        You are an expert Learning Advisor AI. Your goal is to help the user master: "{goal_context}".
        Be encouraging, professional, and provide clear explanations which easy to understand. 
        If they ask about a specific concept, explain it simply. 
        Suggest next steps if they seem stuck.
        Keep responses concise but insightful.
        """
        
        # Convert messages to Gemini format
        history = []
        for msg in messages[:-1]:
            history.append({"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]})
        
        last_message = messages[-1]["content"]
        
        try:
            chat_session = model_v3.start_chat(history=history)
            response = chat_session.send_message(f"System Context: {system_prompt}\n\nUser: {last_message}")
            return response.text
        except Exception as e:
            print(f"DEBUG ERROR: Chat failed: {e}")
            return "I'm sorry, I'm having trouble connecting to my brain right now. Can we try again?"
