from setuptools import setup

setup(
    name="CrunchyFrog example plugin",
    version="0.1",
    py_modules=["example"],
    entry_points="""
    [crunchyfrog.plugin]
    foo = example:ExamplePlugin
    """
)