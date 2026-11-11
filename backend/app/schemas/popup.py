from enum import StrEnum
from typing import Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.website import SuggestedOffer, WebsiteAnalysis


class PopupLayout(StrEnum):
    CENTERED = "centered"
    SPLIT = "split"
    COMPACT = "compact"


class PopupTriggerType(StrEnum):
    TIME_DELAY = "time_delay"
    EXIT_INTENT = "exit_intent"
    SCROLL_PERCENTAGE = "scroll_percentage"


class PopupFont(StrEnum):
    SYSTEM = "system"
    INTER = "inter"
    ROBOTO = "roboto"
    GEORGIA = "georgia"
    MONTSERRAT = "montserrat"
    LATO = "lato"


class PopupTone(StrEnum):
    FRIENDLY = "friendly"
    MINIMAL = "minimal"
    BOLD = "bold"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PopupTrigger(StrictModel):
    type: PopupTriggerType
    delay_seconds: int = Field(default=5, ge=1, le=120)
    scroll_percentage: int = Field(default=50, ge=10, le=95)


class PopupTheme(StrictModel):
    background_color: str
    text_color: str
    accent_color: str
    font: PopupFont
    border_radius: int = Field(ge=0, le=24)

    @field_validator("background_color", "text_color", "accent_color")
    @classmethod
    def validate_hex_color(cls, color: str) -> str:
        if len(color) not in {4, 7} or not color.startswith("#"):
            raise ValueError("Colors must be 3- or 6-digit hex colors")
        try:
            int(color[1:], 16)
        except ValueError as exc:
            raise ValueError("Colors must be valid hexadecimal values") from exc
        return color.upper()


class PopupConfig(StrictModel):
    headline: str = Field(min_length=2, max_length=90)
    description: str = Field(min_length=2, max_length=240)
    cta: str = Field(min_length=2, max_length=40)
    email_placeholder: str = Field(min_length=2, max_length=60)
    offer: SuggestedOffer | None
    layout: PopupLayout
    trigger: PopupTrigger
    theme: PopupTheme
    image: AnyHttpUrl | None
    consent_text: str = Field(min_length=10, max_length=240)


class PopupVariant(StrictModel):
    label: str = Field(pattern="^[ABC]$")
    tone: PopupTone
    config: PopupConfig


class PopupVariants(StrictModel):
    variants: list[PopupVariant] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def require_distinct_labels_and_tones(self) -> Self:
        labels = [variant.label for variant in self.variants]
        tones = [variant.tone for variant in self.variants]
        if set(labels) != {"A", "B", "C"}:
            raise ValueError("Variants must use labels A, B, and C exactly once")
        if len(set(tones)) != 3:
            raise ValueError("Each variant must use a distinct tone")
        return self

    def preserve_analysis_offer(self, analysis: WebsiteAnalysis) -> Self:
        source_offer = analysis.suggested_offer
        for variant in self.variants:
            variant.config.offer = source_offer
        return self


class GeneratePopupsRequest(StrictModel):
    analysis: WebsiteAnalysis


class GeneratePopupsResponse(StrictModel):
    variants: list[PopupVariant] = Field(min_length=3, max_length=3)