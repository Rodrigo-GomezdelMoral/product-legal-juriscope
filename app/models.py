from datetime import date

from pydantic import BaseModel, TypeAdapter


class ArticleVersion(BaseModel):
    norm: str
    published: date
    in_force: date
    text: str
    note: str | None = None


class Article(BaseModel):
    block_id: str
    title: str
    repealed: date | None = None
    versions: list[ArticleVersion]


ARTICLES = TypeAdapter(list[Article])


class Reference(BaseModel):
    block_id: str
    title: str
    url: str


class Citation(Reference):
    version: ArticleVersion
    current: ArticleVersion | None
    repealed: date | None
    see_also: list[Reference]
