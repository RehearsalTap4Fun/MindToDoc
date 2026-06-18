import importlib

def test_registry_starts_empty_then_accepts_register():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)
    assert lib.TAG_REGISTRY == {}

    def noop_patch(ctx):
        pass

    spec = lib.TagSpec(
        name="foo",
        affects=("slice",),
        mutex_group=None,
        description="测试",
        patch=noop_patch,
    )
    lib.register(spec)
    assert "foo" in lib.TAG_REGISTRY
    assert lib.TAG_REGISTRY["foo"].mutex_group is None


def test_register_duplicate_raises():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)

    def noop(ctx):
        pass

    spec = lib.TagSpec("dup", ("slice",), None, "x", noop)
    lib.register(spec)
    try:
        lib.register(spec)
    except ValueError as e:
        assert "dup" in str(e)
    else:
        raise AssertionError("expected ValueError on duplicate register")
