"""
Scientific reference models.

All calculations include citations to enable users to
understand the scientific basis and regulatory requirements.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Reference(BaseModel):
    """A scientific or regulatory reference."""

    id: str = Field(..., description="Unique identifier for the reference")
    title: str = Field(..., description="Title of the reference")
    title_ja: str = Field(default="", description="Japanese title")

    # Author/Source info
    authors: list[str] = Field(default_factory=list)
    organization: str = ""
    organization_ja: str = ""

    # Publication info
    year: Optional[int] = None
    version: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""

    # Description
    description: str = ""
    description_ja: str = ""

    # Section reference (for documents)
    section: str = ""  # e.g., "Section 3.3"
    figure: str = ""  # e.g., "Figure 17"
    table: str = ""  # e.g., "Table 5"

    def get_citation(self) -> str:
        """Get a formatted citation string."""
        parts = []

        if self.authors:
            parts.append(", ".join(self.authors))
        if self.year:
            parts.append(f"({self.year})")
        parts.append(self.title)

        if self.journal:
            parts.append(self.journal)
            if self.volume:
                parts.append(f"Vol. {self.volume}")
            if self.pages:
                parts.append(f"pp. {self.pages}")

        if self.section:
            parts.append(self.section)
        if self.figure:
            parts.append(self.figure)

        return ". ".join(parts)

    def get_short_citation(self) -> str:
        """Get a short citation for inline use."""
        if self.authors and self.year:
            first_author = self.authors[0].split(",")[0] if self.authors else ""
            return f"{first_author} et al., {self.year}"
        if self.organization and self.year:
            return f"{self.organization}, {self.year}"
        return self.title[:50] + "..." if len(self.title) > 50 else self.title
