from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    characters: Mapped[list["Character"]] = relationship(back_populates="owner")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    master_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    default_ruleset_id: Mapped[int | None] = mapped_column(
        ForeignKey("rulesets.id", use_alter=True, name="fk_campaign_default_ruleset"),
        nullable=True,
    )

    rulesets: Mapped[list["Ruleset"]] = relationship(
        back_populates="campaign",
        foreign_keys="Ruleset.campaign_id",
    )


class Ruleset(Base):
    __tablename__ = "rulesets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    campaign: Mapped[Campaign] = relationship(
        back_populates="rulesets",
        foreign_keys=[campaign_id],
    )
    stats: Mapped[list["RulesetStat"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    resources: Mapped[list["RulesetResource"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    derived: Mapped[list["RulesetDerived"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )


class RulesetStat(Base):
    __tablename__ = "ruleset_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    ruleset: Mapped[Ruleset] = relationship(back_populates="stats")
    __table_args__ = (UniqueConstraint("ruleset_id", "key", name="uq_ruleset_stat"),)


class RulesetResource(Base):
    __tablename__ = "ruleset_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), default="#dc2626")
    max_formula: Mapped[str] = mapped_column(String(500), default="0")
    regen_formula: Mapped[str] = mapped_column(String(500), default="0")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    ruleset: Mapped[Ruleset] = relationship(back_populates="resources")
    __table_args__ = (UniqueConstraint("ruleset_id", "key", name="uq_ruleset_resource"),)


class RulesetDerived(Base):
    __tablename__ = "ruleset_derived"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    formula: Mapped[str] = mapped_column(String(500), default="0")
    fallback_formula: Mapped[str] = mapped_column(String(500), default="")
    unit: Mapped[str] = mapped_column(String(16), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    ruleset: Mapped[Ruleset] = relationship(back_populates="derived")
    __table_args__ = (UniqueConstraint("ruleset_id", "key", name="uq_ruleset_derived"),)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_name: Mapped[str] = mapped_column(String(100), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    creation_points_cap: Mapped[int] = mapped_column(Integer, default=20)
    levelup_pool_per_level: Mapped[int] = mapped_column(Integer, default=10)
    notes: Mapped[str] = mapped_column(Text, default="")

    owner: Mapped["User"] = relationship(back_populates="characters")
    stats: Mapped[list["CharacterStat"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    resources: Mapped[list["CharacterResource"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    derived: Mapped[list["CharacterDerived"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    talents: Mapped[list["Talent"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    titles: Mapped[list["Title"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    pets: Mapped[list["Pet"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    inventory: Mapped[list["InventoryItem"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    curses: Mapped[list["Curse"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    quests: Mapped[list["Quest"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class CharacterStat(Base):
    __tablename__ = "character_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    value_initial: Mapped[float] = mapped_column(Float, default=0.0)
    value_creation: Mapped[float] = mapped_column(Float, default=0.0)
    value_invested: Mapped[float] = mapped_column(Float, default=0.0)
    value_levelup: Mapped[float] = mapped_column(Float, default=0.0)
    value_other: Mapped[float] = mapped_column(Float, default=0.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    character: Mapped[Character] = relationship(back_populates="stats")
    __table_args__ = (UniqueConstraint("character_id", "key", name="uq_char_stat"),)


class CharacterResource(Base):
    __tablename__ = "character_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), default="#dc2626")
    max_formula: Mapped[str] = mapped_column(String(500), default="0")
    regen_formula: Mapped[str] = mapped_column(String(500), default="0")
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    character: Mapped[Character] = relationship(back_populates="resources")
    __table_args__ = (UniqueConstraint("character_id", "key", name="uq_char_resource"),)


class CharacterDerived(Base):
    __tablename__ = "character_derived"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    formula: Mapped[str] = mapped_column(String(500), default="0")
    fallback_formula: Mapped[str] = mapped_column(String(500), default="")
    unit: Mapped[str] = mapped_column(String(16), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    item_bonus: Mapped[float] = mapped_column(Float, default=0.0)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    character: Mapped[Character] = relationship(back_populates="derived")
    __table_args__ = (UniqueConstraint("character_id", "key", name="uq_char_derived"),)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[float] = mapped_column(Float, default=0.0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(50), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    parent_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_max: Mapped[bool] = mapped_column(Boolean, default=False)

    character: Mapped[Character] = relationship(back_populates="skills")
    parent: Mapped["Skill | None"] = relationship(
        "Skill", remote_side="Skill.id", backref="children"
    )


class Talent(Base):
    __tablename__ = "talents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str] = mapped_column(String(40), default="")
    origin: Mapped[str] = mapped_column(String(80), default="")
    effect: Mapped[str] = mapped_column(Text, default="")
    stat_bonuses_json: Mapped[dict] = mapped_column(JSON, default=dict)

    character: Mapped[Character] = relationship(back_populates="talents")


class Title(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rarity: Mapped[str] = mapped_column(String(40), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    stat_bonuses_json: Mapped[dict] = mapped_column(JSON, default=dict)

    character: Mapped[Character] = relationship(back_populates="titles")


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    species: Mapped[str] = mapped_column(String(120), default="")
    passive_skill: Mapped[str] = mapped_column(Text, default="")

    character: Mapped[Character] = relationship(back_populates="pets")
    skills: Mapped[list["PetSkill"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan"
    )


class PetSkill(Base):
    __tablename__ = "pet_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[float] = mapped_column(Float, default=0.0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

    pet: Mapped[Pet] = relationship(back_populates="skills")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stats_text: Mapped[str] = mapped_column(Text, default="")
    rarity: Mapped[str] = mapped_column(String(40), default="")
    item_type: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0)

    character: Mapped[Character] = relationship(back_populates="inventory")


class Curse(Base):
    __tablename__ = "curses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    bonus: Mapped[str] = mapped_column(Text, default="")
    malus: Mapped[str] = mapped_column(Text, default="")

    character: Mapped[Character] = relationship(back_populates="curses")


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    progress: Mapped[str] = mapped_column(String(200), default="")
    reward: Mapped[str] = mapped_column(Text, default="")

    character: Mapped[Character] = relationship(back_populates="quests")
