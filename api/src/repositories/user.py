"""Repository for User model with authentication support."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import hash_password, verify_password
from src.models.user import User
from src.repositories.base import BaseRepository
from src.schemas.user import UserCreate


class UserRepository(BaseRepository[User]):
    """Repository for User CRUD operations and authentication."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with User model."""
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get a user by email address.

        Args:
            email: Email address to search for (case-insensitive)

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str, exclude_id: UUID | None = None) -> bool:
        """
        Check if an email address is already registered.

        Args:
            email: Email address to check
            exclude_id: Optional user ID to exclude (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = select(User).where(func.lower(User.email) == email.lower())
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Create a new user with hashed password.

        Args:
            user_in: User creation data including plain text password

        Returns:
            Created user instance
        """
        user_data = {
            "email": user_in.email,
            "hashed_password": hash_password(user_in.password),
            "full_name": user_in.full_name,
        }
        return await self.create(user_data)

    async def authenticate(self, email: str, password: str) -> User | None:
        """
        Authenticate a user by email and password.

        Args:
            email: User's email address
            password: Plain text password to verify

        Returns:
            User if credentials are valid and account is active, None otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def get_active_users(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """
        Get all active users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        result = await self.session.execute(
            select(User)
<<<<<<< HEAD
            .where(User.is_active.is_(True))
=======
            .where(User.is_active)
>>>>>>> d05b5f31ab93b43733b70313ef639e531eec4747
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_password(self, user: User, new_password: str) -> User:
        """
        Update a user's password.

        Args:
            user: User to update
            new_password: New plain text password

        Returns:
            Updated user instance
        """
        return await self.update(
            user,
            {"hashed_password": hash_password(new_password)},
        )

    async def deactivate(self, user: User) -> User:
        """
        Deactivate a user account.

        Args:
            user: User to deactivate

        Returns:
            Updated user instance
        """
        return await self.update(user, {"is_active": False})

    async def activate(self, user: User) -> User:
        """
        Activate a user account.

        Args:
            user: User to activate

        Returns:
            Updated user instance
        """
        return await self.update(user, {"is_active": True})
