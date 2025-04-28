
import os
import json
from flask import Flask, request, jsonify
from langchain_groq import ChatGroq
from flask_cors import CORS
from flask_cors import cross_origin
import ast 
import re

app = Flask(__name__)

# Global dictionary to store the two prompt components.
system_prompt = {
            "manual": """
        You're an AI assistant that reviews customer feedback for restaurants,hotels etc.

        Your task is to:
        1. Identify the overall sentiment in the review (positive, negative, or mixed).
        2. Extract specific problems or complaints (if any).
        3. Suggest actionable, practical solutions to those problems.
        4. Emotional tone detection (angry, satisfied, confused, etc.)
        5. Provide a reply to the customer.

        Your output should strictly follow this JSON format:
        {
        "sentiment": "...",
        "emotional_tone": "...",
        "problems": ["..."],
        "solutions": ["..."],
        "reply": "...",
        "summary": "...",
        }
        """,           
}

API_KEY = "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"
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/api/get_prompt', methods=['GET'])
@cross_origin()
def get_prompt():
    global system_prompt
    if system_prompt["manual"] is None :
        return jsonify({"error": "No system prompt has been set yet."}), 404

    combined_prompt = ""
    if system_prompt["manual"]:
        combined_prompt += system_prompt["manual"]
    return jsonify({"system_prompt": combined_prompt}), 200


@app.route('/api/chat', methods=['POST'])
@cross_origin()
def chat():
    data = request.get_json()
    
    # Check if the required human_message field is provided
    if not data or "human_message" not in data:
        return jsonify({"error": "Please provide a 'human_message' field in the request body."}), 400
    
    # If the API_KEY is not set
    if not API_KEY:
        return jsonify({"error": "API key not set. Please set it via /api/set_api_key."}), 500

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=API_KEY,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    combined_prompt = "\n".join(filter(None, [system_prompt.get("manual")]))

    # Check if human_message is empty or null
    human_message = data.get("human_message", "").strip()
    if not human_message:
        # If human_message is empty or null, use the language parameter
        language = data.get("language", "en")  # Default to English if no language is provided
        full_user_input = f"Please generate a thank-you reply message in {language}."
    else:
        # If human_message is provided, use it as is
        full_user_input = f"Customer Review: {human_message}\n"
    
        # Include form_data if present
        if "form_data" in data and isinstance(data["form_data"], dict):
            full_user_input += "\nStructured Feedback (Form Data):\n"
            full_user_input += json.dumps(data["form_data"], indent=2)

    # Create message list
    messages = []
    if combined_prompt:
        messages.append(("system", combined_prompt))
    messages.append(("human", full_user_input))

    try:
        ai_response = llm.invoke(messages)

        # Try to extract JSON object from the response content
        content = ai_response.content

        # Extract JSON block using regex (matches everything inside outermost `{}`)
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            AI_MSG = json.loads(match.group())
        else:
            AI_MSG = {"error": "Could not extract valid JSON from model response."}
    except Exception as e:
        return jsonify({"error": f"Failed to parse LLM response: {e}"}), 500
    
    return jsonify({"response": AI_MSG}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
