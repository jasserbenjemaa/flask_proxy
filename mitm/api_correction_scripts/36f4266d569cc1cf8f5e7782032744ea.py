import sys
import re

def process_multipart_form_data(raw_data):
    boundary_match = re.search(r'------WebKitFormBoundary[a-zA-Z0-9]+', raw_data)
    if not boundary_match:
        return ""

    boundary = boundary_match.group(0)
    parts = raw_data.split(boundary)
    parts = [part.strip() for part in parts if part.strip()]

    corrected_data = ""
    for part in parts:
        if part.startswith("--"):
            continue

        content_disposition_match = re.search(r'Content-Disposition: form-data; name="([^"]+)"', part)
        if content_disposition_match:
            field_name = content_disposition_match.group(1)
            value = part[content_disposition_match.end():].strip()

            if field_name == "names":
                field_name = "name"

            corrected_data += f'{boundary}\r\n'
            corrected_data += f'Content-Disposition: form-data; name="{field_name}"\r\n'
            corrected_data += '\r\n'
            corrected_data += value + '\r\n'

    corrected_data += f'{boundary}--'

    return corrected_data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_form_data = sys.argv[1]
        corrected_form_data = process_multipart_form_data(raw_form_data)
        print(corrected_form_data)