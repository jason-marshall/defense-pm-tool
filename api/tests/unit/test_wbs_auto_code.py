"""Unit tests for WBS code auto-generation."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.api.v1.endpoints.wbs import _generate_wbs_code
from src.core.exceptions import NotFoundError


def make_mock_wbs(wbs_code: str, path: str = "", level: int = 1):
    """Create a mock WBS element."""
    elem = MagicMock()
    elem.wbs_code = wbs_code
    elem.path = path or wbs_code
    elem.level = level
    return elem


class TestGenerateWBSCodeRoot:
    """Tests for auto-generating root-level WBS codes."""

    @pytest.mark.asyncio
    async def test_first_root_element(self):
        """Should generate '1' when no root elements exist."""
        repo = MagicMock()
        repo.get_root_elements = AsyncMock(return_value=[])
        program_id = uuid4()

        code = await _generate_wbs_code(repo, program_id, None)

        assert code == "1"
        repo.get_root_elements.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_second_root_element(self):
        """Should generate '2' when one root element exists with code '1'."""
        repo = MagicMock()
        repo.get_root_elements = AsyncMock(return_value=[make_mock_wbs("1")])

        code = await _generate_wbs_code(repo, uuid4(), None)

        assert code == "2"

    @pytest.mark.asyncio
    async def test_root_with_gaps(self):
        """Should generate next after max, even with gaps."""
        repo = MagicMock()
        repo.get_root_elements = AsyncMock(
            return_value=[
                make_mock_wbs("1"),
                make_mock_wbs("3"),
                make_mock_wbs("5"),
            ]
        )

        code = await _generate_wbs_code(repo, uuid4(), None)

        assert code == "6"

    @pytest.mark.asyncio
    async def test_root_with_non_numeric_codes(self):
        """Should skip non-numeric codes and start from 1."""
        repo = MagicMock()
        repo.get_root_elements = AsyncMock(
            return_value=[
                make_mock_wbs("PMO"),
                make_mock_wbs("ADMIN"),
            ]
        )

        code = await _generate_wbs_code(repo, uuid4(), None)

        assert code == "1"

    @pytest.mark.asyncio
    async def test_root_with_mixed_codes(self):
        """Should find max among numeric codes, ignoring non-numeric."""
        repo = MagicMock()
        repo.get_root_elements = AsyncMock(
            return_value=[
                make_mock_wbs("1"),
                make_mock_wbs("PMO"),
                make_mock_wbs("3"),
            ]
        )

        code = await _generate_wbs_code(repo, uuid4(), None)

        assert code == "4"


class TestGenerateWBSCodeChild:
    """Tests for auto-generating child WBS codes."""

    @pytest.mark.asyncio
    async def test_first_child(self):
        """Should generate '1.1' for first child of element '1'."""
        repo = MagicMock()
        parent_id = uuid4()
        parent = make_mock_wbs("1", path="1", level=1)
        repo.get_by_id = AsyncMock(return_value=parent)
        repo.get_children = AsyncMock(return_value=[])

        code = await _generate_wbs_code(repo, uuid4(), parent_id)

        assert code == "1.1"

    @pytest.mark.asyncio
    async def test_second_child(self):
        """Should generate '1.2' when '1.1' exists."""
        repo = MagicMock()
        parent_id = uuid4()
        parent = make_mock_wbs("1", path="1", level=1)
        repo.get_by_id = AsyncMock(return_value=parent)
        repo.get_children = AsyncMock(return_value=[make_mock_wbs("1.1", path="1.1", level=2)])

        code = await _generate_wbs_code(repo, uuid4(), parent_id)

        assert code == "1.2"

    @pytest.mark.asyncio
    async def test_nested_child(self):
        """Should generate '1.2.1' for first child of element '1.2'."""
        repo = MagicMock()
        parent_id = uuid4()
        parent = make_mock_wbs("1.2", path="1.2", level=2)
        repo.get_by_id = AsyncMock(return_value=parent)
        repo.get_children = AsyncMock(return_value=[])

        code = await _generate_wbs_code(repo, uuid4(), parent_id)

        assert code == "1.2.1"

    @pytest.mark.asyncio
    async def test_child_with_existing_siblings(self):
        """Should generate next number after existing siblings."""
        repo = MagicMock()
        parent_id = uuid4()
        parent = make_mock_wbs("1.2", path="1.2", level=2)
        repo.get_by_id = AsyncMock(return_value=parent)
        repo.get_children = AsyncMock(
            return_value=[
                make_mock_wbs("1.2.1", path="1.2.1", level=3),
                make_mock_wbs("1.2.2", path="1.2.2", level=3),
                make_mock_wbs("1.2.3", path="1.2.3", level=3),
            ]
        )

        code = await _generate_wbs_code(repo, uuid4(), parent_id)

        assert code == "1.2.4"

    @pytest.mark.asyncio
    async def test_child_parent_not_found(self):
        """Should raise NotFoundError if parent doesn't exist."""
        repo = MagicMock()
        parent_id = uuid4()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await _generate_wbs_code(repo, uuid4(), parent_id)

    @pytest.mark.asyncio
    async def test_child_with_non_numeric_sibling_codes(self):
        """Should skip non-numeric sibling suffixes."""
        repo = MagicMock()
        parent_id = uuid4()
        parent = make_mock_wbs("1", path="1", level=1)
        repo.get_by_id = AsyncMock(return_value=parent)
        repo.get_children = AsyncMock(
            return_value=[
                make_mock_wbs("1.A", path="1.A", level=2),
                make_mock_wbs("1.2", path="1.2", level=2),
            ]
        )

        code = await _generate_wbs_code(repo, uuid4(), parent_id)

        assert code == "1.3"
