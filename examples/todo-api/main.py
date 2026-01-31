from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Cascade TODO Demo")

class Todo(BaseModel):
    id: int
    task: str
    completed: bool = False

todos: List[Todo] = []

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cascade TODO API demo!"}

# TODO: Implement GET /todos
# TODO: Implement POST /todos
