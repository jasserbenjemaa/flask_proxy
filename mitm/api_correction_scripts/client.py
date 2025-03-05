def fix_api(data):
    corrected_data = {}
    if 'nme' in data:
        corrected_data['name'] = data['nme']
    elif 'id' in data:
        corrected_data['name'] = str(data['id'])
    if 'message' in data:
        corrected_data['message'] = data['message']
    if 'source' in data:
        corrected_data['source'] = data['source']
    return corrected_data