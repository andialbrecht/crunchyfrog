from setuptools import setup

setup(
    name="SQL formatter",
    description="Formats the SQL of the current editor",
    version="0.1",
    packages=["sqlformat"],
    license="GPL",
    entry_points="""
    [crunchyfrog.editor]
    sqlformat = sqlformat:SQLFormatterPlugin
    """
)