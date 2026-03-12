from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .ocr import  run_ocr_boarding_pass
from .parser import parse_text_to_boardingpass
from .advisory import generate_advisory
from .config import settings
from datetime import datetime
import os
from .models import BoardingPass, LoungeRecommendation
from .lounges import fetch_lounges_from_bq

app = FastAPI(title="Boarding Pass Advisor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse")
async def parse_endpoint(file: UploadFile = File(None)):
    
    if not file:
        raise HTTPException(status_code=400, detail="Provide image file or text")
    raw_text = ""
    conf = 1.0
    if file:
        content = await file.read()
        #ocr = run_ocr_bytes(content)
        ocr=run_ocr_boarding_pass(content)
        raw_text = ocr["raw_text"]
        conf = ocr["confidence"]
    else:
        raw_text = text
    needs_manual_edit = conf < settings.ocr_confidence_threshold
    try:
        bp = parse_text_to_boardingpass(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"boarding_pass": bp.dict(), "needs_manual_edit": needs_manual_edit, "ocr_confidence": conf}

@app.post("/recommend")
async def recommend_endpoint(bp: BoardingPass):
    if not bp.airport.iata:
        raise HTTPException(status_code=400, detail="Airport IATA required")

    # Current datetime as ISO string (with timezone info? optional)
    current_datetime = datetime.now().isoformat()
    # Fetch ALL lounges for this airport
    all_lounges = fetch_lounges_from_bq(bp.airport.iata)

    # Optional: limit number of lounges to avoid token limits
    MAX_LOUNGES = 50
    if len(all_lounges) > MAX_LOUNGES:
        all_lounges = all_lounges[:MAX_LOUNGES]

    # Unique terminals
    available_terminals = sorted({l.terminal for l in all_lounges if l.terminal})

    # Build payload – send raw times and let LLM handle everything
    payload = {
        "boarding_pass": bp.model_dump(),
        "all_lounges": [l.model_dump() for l in all_lounges],
        "available_terminals": available_terminals,
        "current_datetime": current_datetime,
        "boarding_time_raw": bp.boarding_time_local,
        "departure_time_raw": bp.departure_time_local,
    }
    advisory_result = generate_advisory(payload)
    return advisory_result