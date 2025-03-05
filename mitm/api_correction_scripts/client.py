def fix_api(data):
    corrected_data = {}
    if 'name' in data:
        corrected_data['id'] = data['name']
    elif 'id' in data:
        corrected_data['id'] = data['id']
    
    if 'message' in data:
        corrected_data['msg'] = data['message']
    
    if 'source' in data:
        corrected_data['source'] = data['source']
        
    return corrected_data