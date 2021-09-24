from codecs import open
from os     import path
import setuptools

CURRENT_DIR = path.abspath(path.dirname(__file__))

with open(path.join(CURRENT_DIR, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name                          = "pywebsocket",
    version                       = "1.0",
    author                        = "Ege Bilecen",
    description                   = "Websocket server written in Python.",
    long_description              = long_description,
    long_description_content_type = "text/markdown",
    packages                      = setuptools.find_packages(),
    classifiers                   = [ 
                                        "Programming Language :: Python :: 3", 
                                        "Operating System :: OS Independent",
                                        "Intended Audience :: Developers",
                                        "Topic :: Software Development :: Libraries"
                                    ],
    python_requires               = '>=3.6',
    py_modules                    = ["pywebsocket"],
    install_requires              = []
)
