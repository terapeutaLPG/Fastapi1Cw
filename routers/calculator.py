from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/calc", tags=["calculator"])


class CalcRequest(BaseModel):
    a: float
    b: float


@router.post("/add")
def add(req: CalcRequest):
    return {"result": req.a + req.b, "operation": f"{req.a} + {req.b}"}


@router.post("/subtract")
def subtract(req: CalcRequest):
    return {"result": req.a - req.b, "operation": f"{req.a} - {req.b}"}


@router.post("/multiply")
def multiply(req: CalcRequest):
    return {"result": req.a * req.b, "operation": f"{req.a} * {req.b}"}


@router.post("/divide")
def divide(req: CalcRequest):
    if req.b == 0:
        raise HTTPException(status_code=400, detail="Nie można dzielić przez zero")
    return {"result": req.a / req.b, "operation": f"{req.a} / {req.b}"}
