from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/calc", tags=["calculator"])

@router.get("/add")
def add(
    a: float = Query(..., description="Pierwsza liczba"),
    b: float = Query(..., description="Druga liczba"),
):
    return {"result": a + b, "operation": f"{a} + {b}"}


@router.get("/subtract")
def subtract(
    a: float = Query(..., description="Pierwsza liczba"),
    b: float = Query(..., description="Druga liczba"),
):
    return {"result": a - b, "operation": f"{a} - {b}"}


@router.get("/multiply")
def multiply(
    a: float = Query(..., description="Pierwsza liczba"),
    b: float = Query(..., description="Druga liczba"),
):
    return {"result": a * b, "operation": f"{a} * {b}"}


@router.get("/divide")
def divide(
    a: float = Query(..., description="Pierwsza liczba"),
    b: float = Query(..., description="Druga liczba"),
):
    if b == 0:
        raise HTTPException(status_code=400, detail="Nie można dzielić przez zero")
    return {"result": a / b, "operation": f"{a} / {b}"}
