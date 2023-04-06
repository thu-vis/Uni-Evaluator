from setuptools import setup, Extension
import pybind11, numpy
# python3 -m pybind11 --includes
functions_module = Extension(  
    name ='RangeTree',  
    sources = ['main.cpp'],  
    include_dirs = [pybind11.get_include()],
    extra_compile_args=["-std=c++11"],
    extra_link_args=["-std=c++11"],
    language='c++',
)  
  
setup(ext_modules = [functions_module])
