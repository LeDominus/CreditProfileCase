from fastapi import FastAPI, Request

def load_db_manager(app: FastAPI):
    """Загрузка DatabaseConnector через DI"""
    return app.state.dbConn

def load_conversation_repository(request: Request):
    try:
        return request.app.state.conv_rep
    except AttributeError:
        raise RuntimeError("ConversationRepository не инициализирован в app.state")

def load_profile_repository(request: Request):
    try:
        return request.app.state.profile_rep
    except AttributeError:
        raise RuntimeError("ProfileRepository не инициализирован в app.state")

def load_application_repository(request: Request):
    try:
        return request.app.state.app_rep
    except AttributeError:
        raise RuntimeError("ApplicationRepository не инициализирован в app.state")
    
def load_LLM(request: Request):
    try:
        return request.app.state.llmAPI
    except AttributeError:
        raise RuntimeError("LLMApi не инициализирован в app.state")