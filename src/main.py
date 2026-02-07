from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.models.schemas import NegotiationRequest, NegotiationResult
from src.services.negotiation import NegotiationService
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

negotiation_service = NegotiationService()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/negotiate", response_model=NegotiationResult)
def negotiate(request: NegotiationRequest):
    try:
        result = negotiation_service.negotiate(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
