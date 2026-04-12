from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    create_conversation_from_webhook,
    get_conversation,
    get_conversation_list,
    resolve_conversation,
    send_message,
)
from api.schemas import (
    ApiResponse,
    ConversationListItem,
    SendMessageRequest,
    SendMessageResponse,
    ResolveConversationRequest,
)

app = FastAPI(
    title="智能客服工作台 API",
    description="提供客服工作台所需的所有接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "智能客服工作台 API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/conversations", response_model=ApiResponse)
async def list_conversations():
    return get_conversation_list()


@app.get("/api/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conv(conversation_id: str):
    return get_conversation(conversation_id)


@app.post("/api/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def post_message(conversation_id: str, request: SendMessageRequest):
    request.conversation_id = conversation_id
    return send_message(request)


@app.post("/api/conversations/{conversation_id}/resolve", response_model=ApiResponse)
async def resolve_conv(conversation_id: str, request: ResolveConversationRequest):
    request.conversation_id = conversation_id
    return resolve_conversation(request)


@app.post("/api/webhook/escalation", response_model=ApiResponse)
async def webhook_escalation(payload: dict):
    return create_conversation_from_webhook(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
