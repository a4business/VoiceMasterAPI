from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.docs import get_redoc_html
from sybaseConnector import SybaseConnector
from fastapi.responses import JSONResponse
import json
import os
from fastapi import Body

app = FastAPI(docs_url="/docs", redoc_url="/redocs")

def get_connector():
    try:
        connector = SybaseConnector()
        return connector
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
    
def json_response(data):
    return JSONResponse(content=data, headers={"Content-Type": "application/json"})


@app.get("/")
async def root():
    return {"message": "Hello"}

@app.post("/addAccount", description="Adds a new SIP account to the VoiceMaster database. If sip_password not specified, a random password will be generated.  Returns the details of the newly created account.")
async def add_account( sip_login: str = Body(..., embed=True), sip_password: str = Body(..., embed=True), connector: SybaseConnector = Depends(get_connector)):
    result = connector.addAccount(sip_login, sip_password)
    if isinstance(result, dict) and ("error" in result or "Error" in result):
        raise HTTPException(status_code=503, detail=result.get("error", result.get("Error", "Unknown error")))
    return json_response(result)

@app.get("/getBalance", description="Returns the balance for a given acctid or sip_login in the VoiceMaster database.")
async def get_balance( acctid: int = None, sip_login: str = None, connector: SybaseConnector = Depends(get_connector)):
    return json_response(connector.getBalance(acctid, sip_login))

@app.get("/admin_users", description="Returns a list of all admin users in the VoiceMaster database.")
async def get_users(connector: SybaseConnector = Depends(get_connector)):
    return json_response( connector.getUsers() )
 

@app.get("/account", description="Returns details of all SIP accounts in the VoiceMaster database. Optionally filter by acctid - if not provided, returns all accounts.")
async def get_user(acctid: int = None, sip_login: str = None, connector: SybaseConnector = Depends(get_connector)):
    return json_response(connector.getAccount(acctid, sip_login))




@app.get("/redocs", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title="Custom ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )