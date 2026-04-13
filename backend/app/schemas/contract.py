from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import ContractLanguage


class ContractCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    language: ContractLanguage = ContractLanguage.SOLIDITY
    source: str | None = Field(default=None, max_length=512 * 1024)
    bytecode: str | None = Field(default=None, max_length=512 * 1024)
    compiler_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def check_payload(self) -> "ContractCreate":
        if not self.source and not self.bytecode:
            raise ValueError("either source or bytecode must be provided")
        if self.language == ContractLanguage.BYTECODE and not self.bytecode:
            raise ValueError("bytecode language requires bytecode payload")
        if self.bytecode and not self.bytecode.startswith("0x"):
            raise ValueError("bytecode must start with 0x")
        return self


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    language: ContractLanguage
    compiler_version: str | None = None
    created_at: datetime
