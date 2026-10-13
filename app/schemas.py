"""Pydantic request/response schemas with validation."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .models import CATEGORIES, CONDITIONS, STATUSES

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", re.IGNORECASE)


def validate_name(value: str) -> str:
    value = value.strip()
    if not 2 <= len(value) <= 60:
        raise ValueError("El nombre debe tener entre 2 y 60 caracteres.")
    return value


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if not 5 <= len(value) <= 254 or not EMAIL_RE.fullmatch(value):
        raise ValueError("Introduce un correo válido.")
    return value


def validate_password(value: str) -> str:
    if not 10 <= len(value) <= 128:
        raise ValueError("La contraseña debe tener entre 10 y 128 caracteres.")
    return value


def validate_title(value: str) -> str:
    value = value.strip()
    if not 3 <= len(value) <= 100:
        raise ValueError("El título debe tener entre 3 y 100 caracteres.")
    return value


def validate_description(value: str) -> str:
    value = value.strip()
    if not 10 <= len(value) <= 2000:
        raise ValueError("La descripción debe tener entre 10 y 2000 caracteres.")
    return value


def validate_city(value: str) -> str:
    value = value.strip()
    if not 2 <= len(value) <= 80:
        raise ValueError("La ciudad debe tener entre 2 y 80 caracteres.")
    return value


def validate_category(value: str) -> str:
    value = value.strip()
    if value not in CATEGORIES:
        raise ValueError("Selecciona una categoría válida.")
    return value


def validate_condition(value: str) -> str:
    value = value.strip()
    if value not in CONDITIONS:
        raise ValueError("Estado del producto no válido.")
    return value


def validate_status(value: str) -> str:
    if value not in STATUSES:
        raise ValueError("Estado del producto no válido.")
    return value


def validate_image(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if len(value) > 1000:
        raise ValueError("La URL de la imagen es demasiado larga.")
    if value.startswith("/"):
        # Same-origin media served by this backend (e.g. /media/<id>.png).
        if ".." in value or "//" in value:
            raise ValueError("La ruta de la imagen no es válida.")
        return value
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("La imagen debe tener una URL HTTPS válida.")
    return value


def validate_price(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("El precio debe ser un número entero.")
    if not 1 <= value <= 1_000_000_000:
        raise ValueError("El precio debe estar entre $1 y $1.000.000.000.")
    return value


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileIn(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_name(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class ListingIn(BaseModel):
    title: str
    description: str
    price: int
    category: str
    city: str
    image: str = ""
    condition: str = "Usado"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return validate_title(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return validate_description(value)

    @field_validator("city")
    @classmethod
    def _city(cls, value: str) -> str:
        return validate_city(value)

    @field_validator("category")
    @classmethod
    def _category(cls, value: str) -> str:
        return validate_category(value)

    @field_validator("condition")
    @classmethod
    def _condition(cls, value: str) -> str:
        return validate_condition(value)

    @field_validator("image")
    @classmethod
    def _image(cls, value: str) -> str:
        return validate_image(value)

    @field_validator("price")
    @classmethod
    def _price(cls, value: int) -> int:
        return validate_price(value)


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: int | None = None
    category: str | None = None
    city: str | None = None
    image: str | None = None
    condition: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def _rules(self):
        if self.title is not None:
            self.title = validate_title(self.title)
        if self.description is not None:
            self.description = validate_description(self.description)
        if self.city is not None:
            self.city = validate_city(self.city)
        if self.category is not None:
            self.category = validate_category(self.category)
        if self.condition is not None:
            self.condition = validate_condition(self.condition)
        if self.image is not None:
            self.image = validate_image(self.image)
        if self.price is not None:
            self.price = validate_price(self.price)
        if self.status is not None:
            self.status = validate_status(self.status)
        return self
