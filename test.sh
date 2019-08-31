#!/usr/bin/env bash
sudo Xvfb :99 &
XPID=$!
export DISPLAY=:99
./make.py run --test
EC1=$?
echo exit code ${EC1}
if [[ "$TRAVIS_OS_NAME" = "osx" ]]; then
    dist/PySteamAuth.app/Contents/MacOS/PySteamAuth --test
else
    dist/PySteamAuth --test
fi
EC2=$?
echo exit code ${EC2}
sudo kill ${XPID}
EC=$(( ${EC1} > ${EC2} ? ${EC1} : ${EC2} ))
if (( EC > 0 )); then
    travis_terminate ${EC}
fi