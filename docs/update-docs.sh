#!/usr/bin/env bash
# build docs
git checkout master
mv nofa /tmp/
git checkout gh-pages
git pull
rm -rf *
touch .nojekyll
git checkout master docs
mv /tmp/nofa .
cd docs
make clean
make html
cd ..
mv docs/build/html/* ./
rm -rf docs nofa
git add -A
git commit -m "Publish updated docs"
git push origin gh-pages
# switch back
git checkout master