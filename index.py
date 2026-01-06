# optimize.py
from fastapi import FastAPI
from pydantic import BaseModel
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value
import uvicorn

app = FastAPI()

class OptimizeRequest(BaseModel):
    budget: float
    required_types: list[str] = []
    items: list[dict]  # mỗi dict có: id, type, price, value (rate*noReview hoặc rate)

@app.post("/optimize")
def optimize_plan(req: OptimizeRequest):
    prob = LpProblem("Wedding_Optimization", LpMaximize)

    # Biến quyết định
    x = {}
    for item in req.items:
        x[item['id']] = LpVariable(f"x_{item['id']}", cat='Binary')

    # Hàm mục tiêu: tối đa value
    prob += lpSum(x[item['id']] * item['value'] for item in req.items)

    # Ràng buộc budget
    prob += lpSum(x[item['id']] * item['price'] for item in req.items) <= req.budget

    # Group by type
    items_by_type = {}
    for item in req.items:
        t = item['type'].lower()
        if t not in items_by_type:
            items_by_type[t] = []
        items_by_type[t].append(item)

    # Mỗi type chỉ chọn tối đa 1
    for type_items in items_by_type.values():
        prob += lpSum(x[item['id']] for item in type_items) <= 1

    # Bắt buộc chọn required types (nếu có thể)
    for req_type in req.required_types:
        if req_type.lower() in items_by_type:
            prob += lpSum(x[item['id']] for item in items_by_type[req_type.lower()]) >= 1

    # Giải
    prob.solve()

    selected_ids = [item['id'] for item in req.items if value(x[item['id']]) == 1]
    selected_items = [item for item in req.items if item['id'] in selected_ids]

    total_cost = sum(item['price'] for item in selected_items)
    total_value = sum(item['value'] for item in selected_items)

    return {
        "selected": selected_items,
        "total_cost": total_cost,
        "total_value": total_value,
        "remaining_budget": req.budget - total_cost,
        "status": "optimal" if prob.status == 1 else "infeasible"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)