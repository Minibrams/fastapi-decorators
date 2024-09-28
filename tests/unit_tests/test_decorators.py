import asyncio
import unittest
from functools import partial
from inspect import signature
from typing import Any, Callable

from fastapi_decorators import add_dependencies


class TestAddDependencies(unittest.TestCase):
    def test_sync_function_without_args(self):
        def dependency_func():
            return "dependency"

        @add_dependencies(dependency_func)
        def target_func():
            return "original"

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertEqual(target_func(), "original")

    def test_sync_function_with_args(self):
        def dependency_func():
            return "dependency"

        @add_dependencies(dependency_func)
        def target_func(a, b):
            return a + b

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertEqual(target_func(1, 2), 3)

    def test_async_function_without_args(self):
        async def dependency_func():
            return "dependency"

        @add_dependencies(dependency_func)
        async def target_func():
            return "original"

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)

        result = asyncio.run(target_func())
        self.assertEqual(result, "original")

    def test_async_function_with_args(self):
        async def dependency_func():
            return "dependency"

        @add_dependencies(dependency_func)
        async def target_func(a, b):
            return a + b

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)

        result = asyncio.run(target_func(1, 2))
        self.assertEqual(result, 3)

    def test_multiple_dependencies(self):
        def dep1():
            return "dep1"

        def dep2():
            return "dep2"

        @add_dependencies(dep1, dep2)
        def target_func():
            return "original"

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertIn("__dependency_1", sig.parameters)
        self.assertEqual(target_func(), "original")

    def test_original_function_signature_unchanged(self):
        def dep():
            return "dependency"

        @add_dependencies(dep)
        def target_func(a, b, c=3):
            return a + b + c

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertEqual(target_func(1, 2), 6)

    def test_dependency_parameter_not_passed_to_original_function(self):
        def dep():
            return "dependency"

        @add_dependencies(dep)
        def target_func(*, a, b):
            return a + b

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertIn("a", sig.parameters)
        self.assertIn("b", sig.parameters)

        result = target_func(a=1, b=2)
        self.assertEqual(result, 3)

    def test_dependency_with_default_value(self):
        def dep(x=10):
            return x

        @add_dependencies(dep)
        def target_func():
            return "original"

        sig = signature(target_func)
        dep_param = sig.parameters["__dependency_0"]
        self.assertEqual(dep_param.default, dep)
        self.assertEqual(target_func(), "original")

    def test_wrapper_preserves_function_metadata(self):
        def dep():
            return "dependency"

        @add_dependencies(dep)
        def target_func(a, b):
            """Original function docstring."""
            return a + b

        self.assertEqual(target_func.__name__, "target_func")
        self.assertEqual(target_func.__doc__, "Original function docstring.")

    def test_dependency_as_callable_class(self):
        class Dependency:
            def __call__(self):
                return "dependency"

        dep_instance = Dependency()

        @add_dependencies(dep_instance)
        def target_func():
            return "original"

        sig = signature(target_func)
        self.assertIn("__dependency_0", sig.parameters)
        self.assertEqual(target_func(), "original")

    def test_dependency_with_parameters(self):
        def dep(x, y):
            return x + y

        @add_dependencies(partial(dep, x=1, y=2))
        def target_func():
            return "original"

        sig = signature(target_func)
        self.assertEqual(target_func(), "original")

    def test_integration_with_mock_framework(self):
        # Simulate integration with a framework that uses the function signature
        def dep():
            return "dependency"

        @add_dependencies(dep)
        def target_func(a, b):
            return a + b

        # Simulate a framework extracting parameters
        sig = signature(target_func)
        parameters = sig.parameters

        # Framework would inject dependencies based on signature
        injected_args = {
            "__dependency_0": dep(),
            "a": 1,
            "b": 2,
        }

        result = target_func(**injected_args)
        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
