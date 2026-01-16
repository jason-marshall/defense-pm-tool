"""Unit tests for WBS model properties and methods."""

from uuid import uuid4

from src.models.wbs import WBSElement


class TestWBSElementProperties:
    """Tests for WBSElement model properties."""

    def test_full_path_property(self) -> None:
        """Should return path as string."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1",
            name="Test Element",
            path="1_1",
            level=2,
        )
        assert wbs.full_path == "1_1"

    def test_is_root_true(self) -> None:
        """Should return True for root element."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1",
            name="Root Element",
            path="1",
            level=1,
            parent_id=None,
        )
        assert wbs.is_root is True

    def test_is_root_false(self) -> None:
        """Should return False for non-root element."""
        parent_id = uuid4()
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1",
            name="Child Element",
            path="1_1",
            level=2,
            parent_id=parent_id,
        )
        assert wbs.is_root is False

    def test_is_leaf_true(self) -> None:
        """Should return True for element with no children."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1.1",
            name="Leaf Element",
            path="1_1_1",
            level=3,
        )
        # Children should be empty list by default
        wbs.children = []
        assert wbs.is_leaf is True

    def test_is_leaf_false(self) -> None:
        """Should return False for element with children."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.1",
            name="Parent Element",
            path="1_1",
            level=2,
        )
        # Add a mock child
        child = WBSElement(
            id=uuid4(),
            program_id=wbs.program_id,
            wbs_code="1.1.1",
            name="Child",
            path="1_1_1",
            level=3,
        )
        wbs.children = [child]
        assert wbs.is_leaf is False


class TestWBSElementBuildPath:
    """Tests for WBSElement.build_path method."""

    def test_build_path_root_element(self) -> None:
        """Should return converted wbs_code for root element."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.2.3",
            name="Test",
            path="",
            level=1,
            parent=None,
        )
        assert wbs.build_path() == "1_2_3"

    def test_build_path_child_element(self) -> None:
        """Should build path from parent path and code."""
        parent = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1",
            name="Parent",
            path="1",
            level=1,
        )
        child = WBSElement(
            id=uuid4(),
            program_id=parent.program_id,
            wbs_code="1.2",
            name="Child",
            path="",
            level=2,
            parent=parent,
        )
        assert child.build_path() == "1.2"


class TestWBSElementFilters:
    """Tests for WBSElement filter methods."""

    def test_get_ancestors_filter(self) -> None:
        """Should return SQLAlchemy filter for ancestors."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.2.3",
            name="Test",
            path="1_2_3",
            level=3,
        )
        filter_expr = wbs.get_ancestors_filter()
        # Check it's a SQLAlchemy text expression
        assert filter_expr is not None
        # Check the path is in the expression text
        assert "1_2_3" in str(filter_expr)

    def test_get_descendants_filter(self) -> None:
        """Should return SQLAlchemy filter for descendants."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1.2",
            name="Test",
            path="1_2",
            level=2,
        )
        filter_expr = wbs.get_descendants_filter()
        # Check it's a SQLAlchemy text expression
        assert filter_expr is not None
        # Check the path is in the expression text
        assert "1_2" in str(filter_expr)

    def test_get_children_filter(self) -> None:
        """Should return SQLAlchemy filter for direct children."""
        wbs = WBSElement(
            id=uuid4(),
            program_id=uuid4(),
            wbs_code="1",
            name="Test",
            path="1",
            level=1,
        )
        filter_expr = wbs.get_children_filter()
        # Check it's a SQLAlchemy text expression
        assert filter_expr is not None
        # Check the path is in the expression text
        assert "1" in str(filter_expr)


class TestWBSElementRepr:
    """Tests for WBSElement __repr__ method."""

    def test_repr_format(self) -> None:
        """Should return formatted string representation."""
        wbs_id = uuid4()
        wbs = WBSElement(
            id=wbs_id,
            program_id=uuid4(),
            wbs_code="1.2.3",
            name="Test Element",
            path="1_2_3",
            level=3,
        )
        repr_str = repr(wbs)
        assert "WBSElement" in repr_str
        assert "1.2.3" in repr_str
        assert "1_2_3" in repr_str
        assert "level=3" in repr_str
