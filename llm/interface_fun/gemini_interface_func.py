import os
import google.generativeai as genai
import json
import re
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
sys_instruct="return json object"
# Create the model
generation_config = {
  "temperature": 1,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  system_instruction= sys_instruct,
  generation_config=generation_config,
)


def correct_api(api,api_schema):

  prompt = f"""
  I want the invalid api to be compatible with the api schema. I don't want any data lost :
  invalid api = {api}
  api schema = {api_schema}
  """

  chat_session = model.start_chat()
  response = chat_session.send_message(prompt)
  cleaned_json=response.text
  return json.loads(cleaned_json)

#num_tokens=model.count_tokens([prompt,response.text]) # Count the number of tokens in the response and in the prompt
