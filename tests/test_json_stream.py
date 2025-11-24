import io
import json
from collections import deque
from pathlib import Path

import json_stream
import pytest
from json_stream import to_standard_types

files = Path('.') / "json-test-suite" / "test_parsing"
positive = [
    (file.name, file.read_bytes()) for file in files.iterdir() if file.name.startswith("y_")
]
negative = [
    (file.name, file.read_bytes()) for file in files.iterdir() if file.name.startswith("n_")
]
undefined = [
    (file.name, file.read_bytes()) for file in files.iterdir() if file.name.startswith("i_")
]


class TestJSONStream:
    @pytest.mark.parametrize("filename,content", positive)
    def test_load_positive_scenarios(self, filename: str, content: bytes) -> None:
        with io.BytesIO(content) as binary_file:
            result = json_stream.load(binary_file)
            assert to_standard_types(result) == json.loads(content)

    @pytest.mark.parametrize("filename,content", negative)
    def test_load_negative_scenarios(self, filename: str, content: bytes) -> None:
        with io.BytesIO(content) as binary_file, pytest.raises(Exception):
            print(to_standard_types(json_stream.load(binary_file)))

    @pytest.mark.parametrize("filename,content", positive)
    def test_visit_positive_scenarios(self, filename: str, content: bytes) -> None:
        expected = self._expected_visits(json.loads(content))

        # json-stream will visit duplicate keys separately, so fix up the
        # expected data for those cases
        if filename == "y_object_duplicated_key.json":
            expected.appendleft(('b', ('a',)))
        elif filename == "y_object_duplicated_key_and_value.json":
            expected.appendleft(expected[0])

        def assert_expected(*actual):
            assert expected.popleft() == actual

        with io.BytesIO(content) as binary_file:
            json_stream.visit(binary_file, assert_expected)

    @pytest.mark.parametrize("filename,content", negative)
    def test_visit_negative_scenarios(self, filename: str, content: bytes) -> None:
        with io.BytesIO(content) as binary_file, pytest.raises(Exception):
            json_stream.visit(binary_file, lambda item, path: None)

    @pytest.mark.parametrize("filename,content", undefined)
    def test_undefined_scenarios(self, filename: str, content: bytes) -> None:
        """
        Just check that parser does not crash with segfault or something like that.
        """
        with io.BytesIO(content) as binary_file:
            try:
                json_stream.visit(binary_file, lambda item, path: None)
            except Exception:  # noqa
                pass

        with io.BytesIO(content) as binary_file:
            try:
                result = json_stream.load(binary_file)
                if result is not None and not isinstance(result, (int, float, str, bool)):
                    result.read_all()
            except Exception:  # noqa
                pass

    def _expected_visits(self, obj, path=(), result: deque = None) -> deque[tuple[object, tuple[str, ...]]]:
        if result is None:
            result = deque()
        k = None
        if isinstance(obj, dict):
            for k, v in obj.items():
                self._expected_visits(v, path + (k,), result)
            if k is None:
                result.append((obj, path))
        elif isinstance(obj, list):
            for k, v in enumerate(obj):
                self._expected_visits(v, path + (k,), result)
            if k is None:
                result.append((obj, path))
        else:
            result.append((obj, path))
        return result
