"""Unit tests for UserRepository."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.user import UserCreate


class TestUserRepositoryGetByEmail:
    """Tests for get_by_email method."""

    @pytest.mark.asyncio
    async def test_get_by_email_found(self):
        """Test getting user by email when user exists."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            full_name="Test User",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_email("test@example.com")

        assert result == mock_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self):
        """Test getting user by email when user doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(self):
        """Test that email lookup is case-insensitive."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="Test@Example.com",
            hashed_password="hashed",
            full_name="Test User",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_email("TEST@EXAMPLE.COM")

        assert result == mock_user


class TestUserRepositoryEmailExists:
    """Tests for email_exists method."""

    @pytest.mark.asyncio
    async def test_email_exists_true(self):
        """Test email_exists returns True when email is registered."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            full_name="Test User",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.email_exists("test@example.com")

        assert result is True

    @pytest.mark.asyncio
    async def test_email_exists_false(self):
        """Test email_exists returns False when email is not registered."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.email_exists("nonexistent@example.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_email_exists_with_exclude_id(self):
        """Test email_exists excludes specific user ID."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        exclude_id = uuid4()
        repo = UserRepository(mock_session)
        result = await repo.email_exists("test@example.com", exclude_id=exclude_id)

        assert result is False
        mock_session.execute.assert_called_once()


class TestUserRepositoryCreateUser:
    """Tests for create_user method."""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test creating a new user."""
        mock_session = AsyncMock()
        user_id = uuid4()

        user_in = UserCreate(
            email="new@example.com",
            password="password123",
            full_name="New User",
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_user = User(
                id=user_id,
                email="new@example.com",
                hashed_password="hashed_password",
                full_name="New User",
            )
            mock_create.return_value = mock_user

            result = await repo.create_user(user_in)

            assert result == mock_user
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0][0]
            assert call_args["email"] == "new@example.com"
            assert call_args["full_name"] == "New User"
            assert "hashed_password" in call_args


class TestUserRepositoryAuthenticate:
    """Tests for authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="$2b$12$hashed",
            full_name="Test User",
            is_active=True,
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "get_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            with patch("src.repositories.user.verify_password") as mock_verify:
                mock_verify.return_value = True

                result = await repo.authenticate("test@example.com", "password123")

                assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication fails when user not found."""
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)

        with patch.object(repo, "get_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await repo.authenticate("nonexistent@example.com", "password")

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self):
        """Test authentication fails with wrong password."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="$2b$12$hashed",
            full_name="Test User",
            is_active=True,
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "get_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            with patch("src.repositories.user.verify_password") as mock_verify:
                mock_verify.return_value = False

                result = await repo.authenticate("test@example.com", "wrongpassword")

                assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self):
        """Test authentication fails for inactive user."""
        mock_session = AsyncMock()
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="$2b$12$hashed",
            full_name="Test User",
            is_active=False,
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "get_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            with patch("src.repositories.user.verify_password") as mock_verify:
                mock_verify.return_value = True

                result = await repo.authenticate("test@example.com", "password123")

                assert result is None


class TestUserRepositoryGetActiveUsers:
    """Tests for get_active_users method."""

    @pytest.mark.asyncio
    async def test_get_active_users_default(self):
        """Test getting active users with default pagination."""
        mock_session = AsyncMock()
        mock_users = [
            User(
                id=uuid4(),
                email=f"user{i}@example.com",
                hashed_password="h",
                full_name=f"User {i}",
                is_active=True,
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_active_users()

        assert result == mock_users
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_active_users_with_pagination(self):
        """Test getting active users with pagination."""
        mock_session = AsyncMock()
        mock_users = [
            User(
                id=uuid4(),
                email="user@example.com",
                hashed_password="h",
                full_name="User",
                is_active=True,
            )
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_active_users(skip=10, limit=5)

        assert result == mock_users
        mock_session.execute.assert_called_once()


class TestUserRepositoryUpdatePassword:
    """Tests for update_password method."""

    @pytest.mark.asyncio
    async def test_update_password_success(self):
        """Test updating user password."""
        mock_session = AsyncMock()
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="old_hash",
            full_name="Test User",
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "update", new_callable=AsyncMock) as mock_update:
            updated_user = User(
                id=user.id,
                email="test@example.com",
                hashed_password="new_hash",
                full_name="Test User",
            )
            mock_update.return_value = updated_user

            result = await repo.update_password(user, "newpassword123")

            assert result == updated_user
            mock_update.assert_called_once()
            call_args = mock_update.call_args[0]
            assert call_args[0] == user
            assert "hashed_password" in call_args[1]


class TestUserRepositoryDeactivateActivate:
    """Tests for deactivate and activate methods."""

    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """Test deactivating a user."""
        mock_session = AsyncMock()
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            is_active=True,
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "update", new_callable=AsyncMock) as mock_update:
            deactivated_user = User(
                id=user.id,
                email="test@example.com",
                hashed_password="hash",
                full_name="Test User",
                is_active=False,
            )
            mock_update.return_value = deactivated_user

            result = await repo.deactivate(user)

            assert result == deactivated_user
            mock_update.assert_called_once_with(user, {"is_active": False})

    @pytest.mark.asyncio
    async def test_activate_user(self):
        """Test activating a user."""
        mock_session = AsyncMock()
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            is_active=False,
        )

        repo = UserRepository(mock_session)

        with patch.object(repo, "update", new_callable=AsyncMock) as mock_update:
            activated_user = User(
                id=user.id,
                email="test@example.com",
                hashed_password="hash",
                full_name="Test User",
                is_active=True,
            )
            mock_update.return_value = activated_user

            result = await repo.activate(user)

            assert result == activated_user
            mock_update.assert_called_once_with(user, {"is_active": True})


class TestUserRepositoryInit:
    """Tests for UserRepository initialization."""

    def test_init_sets_model(self):
        """Test that __init__ sets User model."""
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)

        assert repo.model == User
        assert repo.session == mock_session
