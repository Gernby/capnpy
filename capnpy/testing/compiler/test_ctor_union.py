import py
import pytest
from capnpy.testing.compiler.support import CompilerTest

class BaseTestUnionConstructors(CompilerTest):

    @py.test.fixture
    def mod(self):
        schema = """
        @0xbf5147cbbecf40c1;
        struct Shape {
          area @0 :Int64;
          perimeter @1 :Int64;
          union {
            circle @2 :Int64;      # radius
            square @3 :Int64;      # width
            empty  @4 :Void;
          }
        }
        """
        return self.compile(schema)


class TestSpecificCtors(BaseTestUnionConstructors):

    def test_simple(self, mod):
        s = mod.Shape.new_circle(area=1, circle=2, perimeter=3)
        assert s.which() == mod.Shape.__tag__.circle
        assert s.area == 1
        assert s.circle == 2
        assert s.perimeter == 3
        buf = ('\x01\x00\x00\x00\x00\x00\x00\x00'   # area == 1
               '\x03\x00\x00\x00\x00\x00\x00\x00'   # perimeter == 3
               '\x02\x00\x00\x00\x00\x00\x00\x00'   # circle == 2
               '\x00\x00\x00\x00\x00\x00\x00\x00')  # __tag__ == 0 (circle)
        assert s._buf.s == buf
        #
        s = mod.Shape.new_square(area=1, square=2, perimeter=3)
        assert s.which() == mod.Shape.__tag__.square
        assert s.area == 1
        assert s.square == 2
        assert s.perimeter == 3
        buf = ('\x01\x00\x00\x00\x00\x00\x00\x00'   # area == 1
               '\x03\x00\x00\x00\x00\x00\x00\x00'   # perimeter == 3
               '\x02\x00\x00\x00\x00\x00\x00\x00'   # squadre == 2
               '\x01\x00\x00\x00\x00\x00\x00\x00')  # __tag__ == 1 (square)
        assert s._buf.s == buf

    def test_default(self, mod):
        p = mod.Shape.new_circle()
        assert p.circle == 0
        assert p.area == 0
        assert p.perimeter == 0
        assert p.is_circle()
        #
        p = mod.Shape.new_square()
        assert p.square == 0
        assert p.area == 0
        assert p.perimeter == 0
        assert p.is_square()
        #
        p = mod.Shape.new_empty()
        assert p.empty is None
        assert p.area == 0
        assert p.perimeter == 0
        assert p.is_empty()

    def test_no_void_args(self, mod):
        py.test.raises(TypeError, "mod.Shape.new_empty(empty=None)")
        p = mod.Shape.new_empty(1, 2)
        assert p.is_empty()
        assert p.empty is None
        assert p.area == 1
        assert p.perimeter == 2


class TestGenericCtor(BaseTestUnionConstructors):

    def test_simple(self, mod):
        # test the __init__
        s = mod.Shape(area=1, square=2, perimeter=3)
        assert s.which() == mod.Shape.__tag__.square
        assert s.area == 1
        assert s.square == 2
        assert s.perimeter == 3

    def test_void_arg(self, mod):
        s = mod.Shape(area=1, empty=None, perimeter=3)
        assert s.which() == mod.Shape.__tag__.empty
        assert s.area == 1
        assert s.empty is None
        assert s.perimeter == 3

    def test_multiple_tags(self, mod):
        einfo = py.test.raises(TypeError,
                              "mod.Shape(area=0, perimeter=0, circle=1, square=2)")
        assert str(einfo.value) == ('got multiple values for the union tag: '
                                    'square, circle')

    def test_no_tags(self, mod):
        einfo = py.test.raises(TypeError, "mod.Shape(area=0, perimeter=0)")
        assert str(einfo.value) == ("one of the following args is required: "
                                    "circle, square, empty")


    def test_default(self, mod):
        p = mod.Shape(circle=42)
        assert p.area == 0
        assert p.perimeter == 0
        assert p.is_circle()
        assert p.circle == 42
        #
        p = mod.Shape(empty=None)
        assert p.area == 0
        assert p.perimeter == 0
        assert p.is_empty()
