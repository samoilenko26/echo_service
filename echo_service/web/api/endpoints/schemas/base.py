from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, validator

from echo_service.web.api.endpoints.schemas.validators import (
    validate_code,
    validate_path,
)


class DataTypes(str, Enum):
    endpoints = "endpoints"


class Methods(str, Enum):
    get = "GET"
    post = "POST"
    put = "PUT"
    patch = "PATCH"
    delete = "DELETE"


class Response(BaseModel):
    code: int
    headers: Optional[Dict[str, str]]
    body: Optional[str]

    _validate_path = validator("code", allow_reuse=True)(validate_code)


class Attributes(BaseModel):
    verb: Methods
    path: str
    response: Response

    _validate_path = validator("path", allow_reuse=True)(validate_path)


class DataRequest(BaseModel):
    type: DataTypes
    attributes: Attributes


class DataResponse(BaseModel):
    id: str
    type: DataTypes
    attributes: Attributes
