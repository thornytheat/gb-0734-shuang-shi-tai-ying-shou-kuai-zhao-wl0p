from fastapi import Request
from fastapi.responses import JSONResponse


class Problem(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


async def problem_response(request: Request, problem: Problem):
    return JSONResponse({"code": problem.code, "message": problem.message}, status_code=problem.status)
