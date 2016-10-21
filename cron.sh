#!/usr/bin/env bash

VENV_DIR="venv"
REPO_OWNER="g0v"
REPO_NAME="pads2foldrs"
REPO_URL="git@github.com:${REPO_OWNER}/${REPO_NAME}.git"

# gen foldr index
if [ ! -d "${VENV_DIR}" ]; then
  virtualenv "${VENV_DIR}"
  if [ "$?" -ne 0 ]; then
    echo "failed to create virtual environment for python executable."
    exit 1
  fi
fi
eval "source ${VENV_DIR}/bin/activate"
pip install -r requirements.txt
python gen_index.py
if [ "$?" -ne 0 ]; then
  echo "failure: unable to generate foldr index."
  exit 1
fi
eval "deactivate"

# update foldr index to gh-pages
cd _data || exit
git clone ${REPO_URL} --depth 1 -b gh-pages
cp foldrs.json pads2foldrs/
cd pads2foldrs || exit
git add -A .
git commit -m "commit updates"
git push origin gh-pages
cd .. || exit
rm -rf pads2foldrs/
cd ..
