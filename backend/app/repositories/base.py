"""Base repository with generic CRUD operations."""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, UnaryExpression, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

from app.models.orm.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Base repository with generic CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            model: The SQLAlchemy model class.
            session: The async database session.
        """
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        """Get a single record by ID.

        Args:
            id: The UUID of the record.

        Returns:
            The model instance or None if not found.
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_field(
        self, field_name: str, value: Any
    ) -> ModelType | None:
        """Get a single record by field value.

        Args:
            field_name: The name of the field to query.
            value: The value to match.

        Returns:
            The model instance or None if not found.
        """
        stmt = select(self.model).where(
            getattr(self.model, field_name) == value
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_multiple(
        self,
        ids: list[uuid.UUID],
    ) -> Sequence[ModelType]:
        """Get multiple records by IDs.

        Args:
            ids: List of UUIDs.

        Returns:
            Sequence of model instances.
        """
        if not ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str | UnaryExpression[Any] | None = None,
        **filters: Any,
    ) -> Sequence[ModelType]:
        """List records with pagination and filtering.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            order_by: Field name or SQLAlchemy expression to order by.
            **filters: Field-value pairs for filtering.

        Returns:
            Sequence of model instances.
        """
        stmt = select(self.model)

        # Apply filters
        for field_name, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field_name) == value)

        # Apply ordering
        if order_by:
            if isinstance(order_by, str):
                order_field = getattr(self.model, order_by, None)
                if order_field is not None:
                    stmt = stmt.order_by(desc(order_field))
            else:
                stmt = stmt.order_by(order_by)
        else:
            # Default order by created_at descending
            if hasattr(self.model, "created_at"):
                stmt = stmt.order_by(desc(self.model.created_at))

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        """Count records with optional filtering.

        Args:
            **filters: Field-value pairs for filtering.

        Returns:
            Number of matching records.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)

        # Apply filters
        for field_name, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field_name) == value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record.

        Args:
            **kwargs: Field-value pairs for the new record.

        Returns:
            The created model instance.
        """
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def create_many(self, items: list[dict[str, Any]]) -> Sequence[ModelType]:
        """Create multiple records in bulk.

        Args:
            items: List of dictionaries with field-value pairs.

        Returns:
            Sequence of created model instances.
        """
        objs = [self.model(**item) for item in items]
        self.session.add_all(objs)
        await self.session.flush()
        return objs

    async def update(
        self,
        id: uuid.UUID,
        **kwargs: Any,
    ) -> ModelType | None:
        """Update a record by ID.

        Args:
            id: The UUID of the record to update.
            **kwargs: Field-value pairs to update.

        Returns:
            The updated model instance or None if not found.
        """
        obj = await self.get(id)
        if obj is None:
            return None

        for field_name, value in kwargs.items():
            if hasattr(obj, field_name):
                setattr(obj, field_name, value)

        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID.

        Args:
            id: The UUID of the record to delete.

        Returns:
            True if deleted, False if not found.
        """
        obj = await self.get(id)
        if obj is None:
            return False

        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def delete_by_field(self, field_name: str, value: Any) -> int:
        """Delete records by field value.

        Args:
            field_name: The name of the field to query.
            value: The value to match.

        Returns:
            Number of records deleted.
        """
        stmt = select(self.model).where(getattr(self.model, field_name) == value)
        result = await self.session.execute(stmt)
        objs = list(result.scalars().all())

        for obj in objs:
            await self.session.delete(obj)

        await self.session.flush()
        return len(objs)

    async def exists(self, id: uuid.UUID) -> bool:
        """Check if a record exists by ID.

        Args:
            id: The UUID to check.

        Returns:
            True if exists, False otherwise.
        """
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar() is not None

    async def bulk_refresh(self, objs: Sequence[ModelType]) -> None:
        """Refresh multiple objects from the database.

        Args:
            objs: Sequence of model instances to refresh.
        """
        for obj in objs:
            await self.session.refresh(obj)
