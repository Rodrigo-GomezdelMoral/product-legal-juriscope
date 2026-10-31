import base64
from typing import Annotated

from fastapi import Header, HTTPException
from pydantic import BaseModel

from app.telemetry import identify

ROLE = "Juriscope.User"
OBJECT_ID = "http://schemas.microsoft.com/identity/claims/objectidentifier"
ROLES = "roles"


class PrincipalClaim(BaseModel):
    typ: str
    val: str


class Principal(BaseModel):
    claims: list[PrincipalClaim]
    name_typ: str
    role_typ: str


class User(BaseModel):
    id: str
    name: str


def signed_in(principal: Annotated[str | None, Header(alias="X-MS-CLIENT-PRINCIPAL")] = None) -> User:
    try:
        parsed = Principal.model_validate_json(base64.b64decode(principal or "", validate=True))
    except ValueError as error:
        raise HTTPException(401, "Sign in to use Juriscope.") from error
    claims = {claim.typ: claim.val for claim in parsed.claims}
    if not (user_id := claims.get(OBJECT_ID) or claims.get("oid")):
        raise HTTPException(401, "The sign-in carries no user id.")
    if ROLE not in {claim.val for claim in parsed.claims if claim.typ in {parsed.role_typ, ROLES}}:
        raise HTTPException(403, "Your account is not assigned to Juriscope.")
    identify(user_id)
    return User(id=user_id, name=claims.get(parsed.name_typ, ""))
