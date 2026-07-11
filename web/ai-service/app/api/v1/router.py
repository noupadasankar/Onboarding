"""Central v1 router. Mount all feature routers here.

Each increment adds its router to this file:
  Increment 2:  chat placeholder
  Increment 3:  documents (ingestion, list, get, delete)
  Increment 4:  processing (chunk pipeline, chunk retrieval)
  Increment 6:  vectorstore (index, health, count)
  Increment 7:  search (retrieval pipeline)
  Increment 9:  agents
"""
from fastapi import APIRouter

from app.api.v1 import chat, documents, health, processing, search, vectorstore

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(processing.router)
api_router.include_router(vectorstore.router)
api_router.include_router(search.router)
