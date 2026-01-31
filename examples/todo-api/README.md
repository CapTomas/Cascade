# Cascade Example: TODO API

This example demonstrates how Cascade can be used to manage a simple FastAPI project.

## Project Structure
- `main.py`: Simple FastAPI application.
- `requirements.txt`: Project dependencies.
- `.cascade/`: Cascade project database and configuration.

## How to use this example

1. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn
   ```

2. **Explore tickets**:
   ```bash
   ccd ticket list
   ```

3. **Check project status**:
   ```bash
   ccd status
   ```

4. **Execute the next task**:
   ```bash
   ccd next
   ```

## Demo Scenario
This project is initialized with several tickets:
- `Ticket #1`: Implement GET /todos endpoint.
- `Ticket #2`: Implement POST /todos endpoint.
- `Ticket #3`: Add unit tests for API.

Try running `ccd ticket execute 1` to see how Cascade handles the development of the GET endpoint.
