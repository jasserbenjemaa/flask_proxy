import google.generativeai as genai # type: ignore
import os
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
sys_instruct="fix the provided JSON by using the given schema and return json object"
# Create the model
generation_config = {
  "temperature": 0.3,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  system_instruction=sys_instruct,
  generation_config=generation_config,
)

def correct_json(api,api_schema):
  prompt = f"""
  api_schema = {api_schema}
  wrong_api: {api}
"""

  chat_session = model.start_chat()
  response = chat_session.send_message(prompt)
  num_tokens=model.count_tokens([prompt,response.text]) # Count the number of tokens in the response and in the prompt
  return response.text


#########################################################################OR#########################################################################

#response = client.models.generate_content(
#    model='gemini-2.0-flash',
#    contents='What type of instrument is an oboe?',
#    config={
#        'response_mime_type': 'text/x.enum',
#        'response_schema': {
#            "type": "STRING",
#            "enum": ["Percussion", "String", "Woodwind", "Brass", "Keyboard"],
#        },
#    },
#)