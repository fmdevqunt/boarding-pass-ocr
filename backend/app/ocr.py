from google.cloud import vision_v1
from datetime import datetime, timedelta
#from pydantic_settings import BaseSettings



client = vision_v1.ImageAnnotatorClient()

def run_ocr_boarding_pass(image_bytes: bytes):
    image = vision_v1.Image(content=image_bytes)
    
    # DOCUMENT_TEXT_DETECTION is best for dense/structured text like boarding passes
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"API Error: {response.error.message}")

    full_text = ""
    word_confidences = []
    
    annotation = response.full_text_annotation
    if annotation:
        full_text = annotation.text
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        # Collect word-level confidence for better accuracy mapping
                        word_confidences.append(word.confidence)

    avg_conf = sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
    
    return {
        "raw_text": full_text,
        "confidence": avg_conf,
        "language": annotation.pages[0].property.detected_languages[0].language_code if annotation.pages else "unknown"
    }




client = vision_v1.ImageAnnotatorClient()

def decode_boarding_pass_barcode(image_bytes: bytes):
    """
    Detects PDF417 barcode in a boarding pass image and extracts:
      - airport_iata
      - destination
      - flight_number
      - date (Julian → calendar)
    """
    print('=================hello')
    # Use DOCUMENT_TEXT_DETECTION (BARCODE_DETECTION removed in many versions)
    request = {
        "image": {"content": image_bytes},
        "features": [{"type": vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION}],
    }
    print('=================hello1')
    response = client.annotate_image(request)
    print('=================hello2')
    # PDF417 barcodes appear in response.text_annotations[0].description
    raw = None
    for entity in response.text_annotations:
        if "PDF417" in entity.description or len(entity.description) > 60:
            raw = entity.description.strip()
            break

    # If still no raw barcode, try full_text_annotation
    if not raw and response.full_text_annotation.text:
        text = response.full_text_annotation.text
        if len(text) > 60:
            raw = text.strip()

    if not raw:
        return {
            "airport_iata": None,
            "destination": None,
            "flight_number": None,
            "date": None,
            "raw": None,
        }

    # BCBP must be at least 51 chars
    if len(raw) < 51:
        return {
            "airport_iata": None,
            "destination": None,
            "flight_number": None,
            "date": None,
            "raw": raw,
        }

    try:
        airport_iata = raw[30:33].strip()
        destination = raw[33:36].strip()
        carrier = raw[36:39].strip()
        flight_num_raw = raw[39:44].strip()
        julian_str = raw[44:47].strip()

        flight_number = f"{carrier}{flight_num_raw.lstrip('0')}"

        year = datetime.now().year
        day_of_year = int(julian_str)
        date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)

    except Exception:
        airport_iata = destination = flight_number = date = None

    return {
        "airport_iata": airport_iata or None,
        "destination": destination or None,
        "flight_number": flight_number or None,
        "date": date,
        "raw": raw,
    }

if __name__ == "__main__":


    with open('paper-boarding-pass.png', "rb") as f:
        img_bytes = f.read()

    result = decode_boarding_pass_barcode(img_bytes)
    print('======barcode=======')
    print(result)


    result = run_ocr_boarding_pass(img_bytes)
    print('======ocr======')
    
    print(result)