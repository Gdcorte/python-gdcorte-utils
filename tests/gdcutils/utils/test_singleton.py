"""SIngleton Tests."""

from gdcutils.utils.singleton import Singleton


def test_unit_it_only_single_instance_is_creatable() -> None:
    """Test Multiple instantiation will not reuse single instance."""

    class SingleTest(metaclass=Singleton):
        """Test Class."""

    instance_1 = SingleTest()
    instance_2 = SingleTest()

    assert instance_1 is instance_2


def test_unit_it_can_have_child_classes_as_singletons_too() -> None:
    """Test child of singletons are still singletons."""

    class ParentTest(metaclass=Singleton):
        """Test Class."""

    class ChildTest(metaclass=Singleton):
        """Test Class."""

    parent = ParentTest()

    child_1 = ChildTest()
    child_2 = ChildTest()

    assert child_1 is child_2
    assert child_1 is not parent  # type: ignore[comparison-overlap]
