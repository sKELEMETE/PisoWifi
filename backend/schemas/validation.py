from pydantic import BaseModel, Field, field_validator
import re

MAC_REGEX = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"


class MacRequest(BaseModel):
    mac: str = Field(..., min_length=17, max_length=17)

    @field_validator("mac")
    @classmethod
    def validate_mac(cls, v):
        if not re.match(MAC_REGEX, v):
            raise ValueError("Invalid MAC format")
        return v.upper()


class CoinRequest(BaseModel):
    value: int = Field(..., ge=1, le=1000)


class VoucherRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)

    @field_validator("code")
    @classmethod
    def clean_code(cls, v):
        return v.strip().upper()
