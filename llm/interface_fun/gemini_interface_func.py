import os
import google.generativeai as genai
import json
import re
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
sys_instruct="return json object"
# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  system_instruction= sys_instruct,
  generation_config=generation_config,
)

def clean_json_string(json_str):
    # Remove markdown code block markers and any newlines at the start
    json_str = re.sub(r'^```json\s*\n', '', json_str)
    json_str = re.sub(r'\n```$', '', json_str)
    return json_str.strip()

def correct_api(api,api_schema):

  prompt = f"""
  i want you to change the value of each key but don't touch the keys give a random name random age:
  api = {api}
  Return: list[Recipe]
  """

  chat_session = model.start_chat()
  response = chat_session.send_message(prompt)
  cleaned_json=clean_json_string(response.text)
  return json.loads(cleaned_json)

#num_tokens=model.count_tokens([prompt,response.text]) # Count the number of tokens in the response and in the prompt
