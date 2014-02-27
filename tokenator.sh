#!/bin/bash
#
# yum install oathtool xdotool
#

TOKEN=`/usr/bin/oathtool --totp <HASH>`
/usr/bin/xdotool type "$TOKEN"
