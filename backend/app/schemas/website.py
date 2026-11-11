from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class AnalyzeWebsiteRequest(BaseModel):
    url: AnyHttpUrl


class SuggestedOffer(BaseModel):
    text: str = Field(min_length=1, max_length=240)
    requires_owner_approval: bool


class WebsiteAnalysis(BaseModel):
    business_type: str = Field(min_length=2, max_length=120)
    target_audience: str = Field(min_length=2, max_length=240)
    brand_tone: str = Field(min_length=2, max_length=120)
    products: list[str] = Field(min_length=1, max_length=12)
    brand_colors: list[str] = Field(max_length=12)
    suggested_offer: SuggestedOffer

    @field_validator("brand_colors")
    @classmethod
    def validate_brand_colors(cls, colors: list[str]) -> list[str]:
        for color in colors:
            if len(color) not in {4, 7} or not color.startswith("#"):
                raise ValueError("Brand colors must be 3- or 6-digit hex colors")
            try:
                int(color[1:], 16)
            except ValueError as exc:
                raise ValueError("Brand colors must be valid hexadecimal values") from exc
        return [color.upper() for color in colors]


class WebsiteAnalysisResponse(BaseModel):
    website_id: UUID
    url: AnyHttpUrl
    analysis: WebsiteAnalysis


class _GeminiResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidates: list[dict]