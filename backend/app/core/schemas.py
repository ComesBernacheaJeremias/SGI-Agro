"""Base de los schemas Pydantic (entrada/salida de la API)."""

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Schema base: lee atributos de modelos ORM y rechaza campos desconocidos."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")
