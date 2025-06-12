import json

from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime
import enum

Base = declarative_base()

class RouteStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Таблица для связи many-to-many между Account и Route
# account_route = Table(
#     'account_route',
#     Base.metadata,
#     Column('account_id', Integer, ForeignKey('accounts.id')),
#     Column('route_id', Integer, ForeignKey('routes.id'))
# )


class Account(Base):
    __tablename__ = 'accounts'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    proxy: Mapped[str] = mapped_column(nullable=True)
    user_agent: Mapped[str] = mapped_column(nullable=True)
    os_user_agent: Mapped[str] = mapped_column(nullable=True)
    chrome_version: Mapped[str] = mapped_column(nullable=True)

    # blockchains
    # evm_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    evm_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=True)
    evm_address: Mapped[str] = mapped_column(nullable=True)
    # aptos_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    aptos_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=True)
    aptos_address: Mapped[str] = mapped_column(nullable=True)
    # aptos_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    solana_private_key: Mapped[str] = mapped_column(unique=True, index=True, nullable=True)
    solana_address: Mapped[str] = mapped_column(nullable=True)

    # socials
    twitter_token: Mapped[str] = mapped_column(nullable=True)
    ct0: Mapped[str] = mapped_column(nullable=True)
    discord_token: Mapped[str] = mapped_column(nullable=True)
    email_address: Mapped[str] = mapped_column(nullable=True)
    email_password: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Связь many-to-many с Route
    # routes = relationship('Route', secondary=account_route, back_populates='accounts')
    # Связь one-to-one с Route
    route = relationship('Route', back_populates='account', uselist=False)

    def __repr__(self):
        return f"Name: {self.name}, EVM address: {self.evm_address}"


class SpareProxy(Base):
    """Модель для хранения запасных прокси"""
    __tablename__ = 'spare_proxies'

    id: Mapped[int] = mapped_column(primary_key=True)
    proxy: Mapped[str] = mapped_column(unique=True, index=True)
    in_use: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self):
        return f"SpareProxy(proxy={self.proxy}, in_use={self.in_use})"


class Route(Base):
    __tablename__ = 'routes'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[RouteStatus] = mapped_column(default=RouteStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Связь many-to-many с Account
    account = relationship('Account', back_populates='route')
    actions = relationship('RouteAction', back_populates='route', cascade='all, delete-orphan', order_by='RouteAction.order_index')

    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), nullable=False)

    def __repr__(self):
        return f"Route(id={self.id}, status={self.status})"

    def __iter__(self):
        return [action for action in self.actions]


class RouteAction(Base):
    __tablename__ = 'route_actions'

    id: Mapped[int] = mapped_column(primary_key=True)
    action_name: Mapped[str] = mapped_column(nullable=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id', ondelete='CASCADE'), nullable=False)
    action_type: Mapped[str] = mapped_column(nullable=False)
    # action_params: Mapped[str] = mapped_column(nullable=False)
    params_id: Mapped[int] = mapped_column(ForeignKey('action_params.id'), nullable=False, default=1)
    status: Mapped[RouteStatus] = mapped_column(default=RouteStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    order_index: Mapped[int] = mapped_column(nullable=False, default=0)

    # Связь many-to-one с Route
    route = relationship("Route", back_populates="actions")
    # Связь many-to-one с ActionParams
    # params = relationship("ActionParams", foreign_keys=[params_id]) #  back_populates="route_actions"
    params: Mapped["ActionParams"] = relationship(
        "ActionParams",
        cascade="all, delete-orphan",
        single_parent=True
    )

    def __repr__(self):
        return f"RouteAction(type={self.action_type}, status={self.status})"

    def __str__(self):
        return f"RouteAction: {self.action_name}"


class ActionParams(Base):
    __tablename__ = 'action_params'

    id: Mapped[int] = mapped_column(primary_key=True)
    action_params: Mapped[str] = mapped_column(nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
