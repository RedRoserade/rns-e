#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2026 André Carvalho
# SPDX-License-Identifier: Apache-2.0

set -e

ip link set can0 type can bitrate 100000
ip link set can0 up
