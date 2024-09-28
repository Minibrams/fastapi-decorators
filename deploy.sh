set -e

rm -rf dist
rm -rf build

pip install -r requirements.txt
python setup.py sdist bdist_wheel

twine check dist/*
twine upload dist/*
